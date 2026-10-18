"""Read the Balances table out of a Lua 5.3 wasm32 memory image.

This does not call the module. The layout was measured on checkpoint
``ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk``:

- Short strings (GC tag 4): 16-byte header, length in the shrlen byte, bytes at +16.
- Long strings (GC tag 20): 16-byte header, length as a u32 at +12, bytes at +16.
- TValue is 16 bytes: 8-byte payload, then a u32 type tag.
  A collectable string uses tag 68 (short) or 84 (long). A table uses tag 69.
  The pointer is the low 4 bytes of the payload.
- A table header is 32 bytes: next, tag/mark/flags/lsizenode, sizearray,
  array, node, lastfree, metatable, gclist.
- Hash nodes are 32 bytes: value TValue, then key TValue.
- Each balance is a 512-bit lua-bint: a table with a 16-element array.
  Each limb is the low 32 bits of a TValue whose type tag is 19.
  Limbs are little-endian. The top bit of limb 15 is the sign.
"""

from __future__ import annotations

import struct
from typing import Iterable

SHORT_STRING = 4
LONG_STRING = 20
TABLE = 5
TV_SHORT = 68
TV_LONG = 84
TV_TABLE = 69
TV_BOOL = 1
LIMBS = 16
WORD_BITS = 32


class MemoryLayoutError(Exception):
    pass


def _u32(mem: bytes, offset: int) -> int:
    return struct.unpack_from("<I", mem, offset)[0]


def read_string(mem: bytes, obj: int) -> bytes | None:
    if obj <= 0 or obj + 16 >= len(mem):
        return None
    tag = mem[obj + 4]
    if tag == SHORT_STRING:
        length = mem[obj + 7]
        end = obj + 16 + length
        if end > len(mem):
            return None
        return mem[obj + 16 : end]
    if tag == LONG_STRING:
        length = _u32(mem, obj + 12)
        if length > 1_000_000:
            return None
        end = obj + 16 + length
        if end > len(mem):
            return None
        return mem[obj + 16 : end]
    return None


def find_short_string(mem: bytes, text: str) -> int:
    raw = text.encode()
    blob = raw + b"\x00"
    start = 0
    while True:
        index = mem.find(blob, start)
        if index < 0:
            raise MemoryLayoutError(f"interned string not found: {text}")
        obj = index - 16
        if obj >= 0 and mem[obj + 4] == SHORT_STRING and mem[obj + 7] == len(raw):
            return obj
        start = index + 1


def _table_header(mem: bytes, obj: int) -> dict | None:
    if obj <= 0 or obj + 32 > len(mem) or mem[obj + 4] != TABLE:
        return None
    array, node, lastfree, metatable, gclist = struct.unpack_from("<IIIII", mem, obj + 12)
    return {
        "lsizenode": mem[obj + 7],
        "sizearray": _u32(mem, obj + 8),
        "array": array,
        "node": node,
        "lastfree": lastfree,
        "metatable": metatable,
        "gclist": gclist,
    }


def _tvalue(mem: bytes, offset: int) -> tuple[int, int, int]:
    low, high, tag = struct.unpack_from("<III", mem, offset)
    return low, high, tag


def _find_key_hits(mem: bytes, obj: int, tv_tag: int) -> Iterable[int]:
    pattern = struct.pack("<I", obj) + b"\x00\x00\x00\x00" + struct.pack("<I", tv_tag)
    start = 0
    while True:
        index = mem.find(pattern, start)
        if index < 0:
            return
        yield index
        start = index + 1


def find_balances_table(mem: bytes) -> int:
    """Return the address of the live Balances table (the large hash table)."""
    key = find_short_string(mem, "Balances")
    found: list[int] = []
    for hit in _find_key_hits(mem, key, TV_SHORT):
        if hit < 16:
            continue
        low, _high, tag = _tvalue(mem, hit - 16)
        if tag != TV_TABLE:
            continue
        header = _table_header(mem, low)
        if header is None:
            continue
        if header["lsizenode"] >= 12 and header["sizearray"] == 0:
            found.append(low)
    if len(found) != 1:
        raise MemoryLayoutError(f"expected one live Balances table, found {found}")
    return found[0]


def _limb(mem: bytes, offset: int) -> int:
    low = _u32(mem, offset)
    high = _u32(mem, offset + 4)
    tag = _u32(mem, offset + 8)
    if tag != 19:
        raise MemoryLayoutError(f"bint limb type tag {tag} at {offset}")
    if high != 0:
        raise MemoryLayoutError(f"bint limb high bits {high:#x} at {offset}")
    return low


def read_bint(mem: bytes, obj: int) -> int:
    header = _table_header(mem, obj)
    if header is None:
        raise MemoryLayoutError(f"balance value {obj:#x} is not a table")
    if header["sizearray"] != LIMBS:
        raise MemoryLayoutError(
            f"balance table {obj:#x} sizearray {header['sizearray']}, expected {LIMBS}"
        )
    array = header["array"]
    if array <= 0 or array + LIMBS * 16 > len(mem):
        raise MemoryLayoutError(f"balance array pointer {array:#x} is outside memory")
    value = 0
    for index in range(LIMBS):
        value |= _limb(mem, array + index * 16) << (WORD_BITS * index)
    if value >= (1 << (LIMBS * WORD_BITS - 1)):
        value -= 1 << (LIMBS * WORD_BITS)
    return value


def read_balance_map(mem: bytes, table: int | None = None) -> tuple[dict[str, str], dict]:
    if table is None:
        table = find_balances_table(mem)
    header = _table_header(mem, table)
    if header is None:
        raise MemoryLayoutError("Balances header is not a table")
    slots = 1 << header["lsizenode"]
    node = header["node"]
    if node <= 0 or node + slots * 32 > len(mem):
        raise MemoryLayoutError("Balances node array is outside memory")
    balances: dict[str, str] = {}
    metatables: dict[int, int] = {}
    odd_values = 0
    for slot in range(slots):
        off = node + slot * 32
        key_low, _key_high, key_tag = _tvalue(mem, off + 16)
        if key_tag == 0:
            continue
        # wasm32 stores the GC pointer in the low 4 bytes. The high 4 bytes
        # are not always cleared.
        if key_tag not in (TV_SHORT, TV_LONG):
            odd_values += 1
            continue
        raw = read_string(mem, key_low)
        if raw is None:
            odd_values += 1
            continue
        try:
            address = raw.decode("ascii")
        except UnicodeError:
            odd_values += 1
            continue
        val_low, _val_high, val_tag = _tvalue(mem, off)
        if val_tag != TV_TABLE:
            odd_values += 1
            continue
        amount = read_bint(mem, val_low)
        meta = _table_header(mem, val_low)["metatable"]
        metatables[meta] = metatables.get(meta, 0) + 1
        if address in balances:
            raise MemoryLayoutError(f"duplicate Balances key {address}")
        balances[address] = str(amount)
    info = {
        "table": table,
        "slots": slots,
        "lsizenode": header["lsizenode"],
        "rows": len(balances),
        "odd_values": odd_values,
        "metatables": {str(key): count for key, count in metatables.items()},
    }
    return balances, info


def _globals_table_covering(mem: bytes, node_address: int) -> int:
    """Find the table whose hash array contains ``node_address``."""
    # Table headers are 4-byte aligned and carry GC tag 5 at byte +4.
    limit = len(mem) - 32
    offset = 0
    found: list[int] = []
    while offset <= limit:
        if mem[offset + 4] != TABLE:
            offset += 4
            continue
        lsizenode = mem[offset + 7]
        if 4 <= lsizenode <= 16:
            node = _u32(mem, offset + 16)
            size = 1 << lsizenode
            end = node + size * 32
            if node <= node_address < end and (node_address - node) % 32 == 0:
                found.append(offset)
        offset += 4
    if len(found) != 1:
        raise MemoryLayoutError(f"expected one globals table, found {found}")
    return found[0]


def read_flag(mem: bytes, table: int, name: str) -> bool:
    header = _table_header(mem, table)
    if header is None:
        raise MemoryLayoutError("flag table is not a table")
    slots = 1 << header["lsizenode"]
    node = header["node"]
    want = name.encode()
    for slot in range(slots):
        off = node + slot * 32
        key_low, _key_high, key_tag = _tvalue(mem, off + 16)
        if key_tag == 0:
            continue
        raw = read_string(mem, key_low)
        if raw != want:
            continue
        low, _high, tag = _tvalue(mem, off)
        if tag != TV_BOOL or low not in (0, 1):
            raise MemoryLayoutError(f"{name} is not a boolean (tag {tag}, value {low})")
        return low == 1
    raise MemoryLayoutError(f"{name} is not in the globals table")


def read_checkpoint_state(mem: bytes) -> dict:
    balances_table = find_balances_table(mem)
    # The Balances key node sits 16 bytes before a matching key TValue.
    key = find_short_string(mem, "Balances")
    node_address = None
    for hit in _find_key_hits(mem, key, TV_SHORT):
        if hit < 16:
            continue
        low, _high, tag = _tvalue(mem, hit - 16)
        if tag == TV_TABLE and low == balances_table:
            node_address = hit - 16
            break
    if node_address is None:
        raise MemoryLayoutError("Balances key node was not found")
    globals_table = _globals_table_covering(mem, node_address)
    balances, info = read_balance_map(mem, balances_table)
    flags = {
        "IS_STOPPED": read_flag(mem, globals_table, "IS_STOPPED"),
        "TRANSFERS_ENABLED": read_flag(mem, globals_table, "TRANSFERS_ENABLED"),
        "DEPOSITS_ENABLED": read_flag(mem, globals_table, "DEPOSITS_ENABLED"),
        "WITHDRAWALS_ENABLED": read_flag(mem, globals_table, "WITHDRAWALS_ENABLED"),
    }
    info["globals_table"] = globals_table
    info["flags"] = flags
    return {"balances": balances, "info": info}
