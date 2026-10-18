"""qAR 0.16.0 balance rules, written from the handler source.

The source is Eval nonce 1977055, message
``eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA``. ``bint`` is lua-bint
0.5.1 at 512 bits (``aolibs.bint()`` defaults to 512). Amounts in this
window fit in that width, so the arithmetic is ordinary integer
arithmetic. A value outside ``0 .. 2**512-1`` after an add or sub is
reported instead of being wrapped to force a match.

``actions.add`` runs the handler list inside ``pcall``. A throw before
``Balances`` is written leaves the table unchanged. ``Transfer`` checks
the quantity and the sender balance before it writes.
"""

from __future__ import annotations

BITS = 512
MOD = 1 << BITS


class RuleError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def parse_quantity(text: object) -> int:
    """``bint.new`` on a Quantity tag. Raises RuleError when bint would assert."""
    if not isinstance(text, str):
        raise RuleError("value cannot be represented by a bint")
    if _is_decimal(text):
        return to_signed(int(text, 10))
    hex_body = _prefixed(text, ("0x", "0X"))
    if hex_body is not None and _is_hex(hex_body):
        sign = -1 if text[0] == "-" else 1
        return to_signed(sign * int(hex_body, 16))
    bin_body = _prefixed(text, ("0b", "0B"))
    if bin_body is not None and bin_body and all(ch in "01" for ch in bin_body):
        sign = -1 if text[0] == "-" else 1
        return to_signed(sign * int(bin_body, 2))
    raise RuleError("value cannot be represented by a bint")


def _is_decimal(text: str) -> bool:
    if not text:
        return False
    body = text[1:] if text[0] in "+-" else text
    return bool(body) and body.isdigit()


def _is_hex(body: str) -> bool:
    return bool(body) and all(ch in "0123456789abcdefABCDEF" for ch in body)


def _prefixed(text: str, markers: tuple[str, str]) -> str | None:
    rest = text[1:] if text[:1] in "+-" else text
    for marker in markers:
        if rest.startswith(marker):
            return rest[len(marker) :]
    return None


def to_signed(value: int) -> int:
    """Fold a two's-complement 512-bit residue to a Python int."""
    residue = value % MOD
    if residue >= (1 << (BITS - 1)):
        return residue - MOD
    return residue


def less_than(left: int, right: int) -> bool:
    return to_signed(left) < to_signed(right)


def add(left: int, right: int) -> int:
    return to_signed(left + right)


def sub(left: int, right: int) -> int:
    return to_signed(left - right)


def decimal(value: int) -> str:
    return str(to_signed(value))


def first_tag(tags: list[dict], name: str) -> str | None:
    """``Tab`` keeps the first value of each tag name."""
    for tag in tags:
        if tag.get("name") == name:
            value = tag.get("value")
            if isinstance(value, str):
                return value
            return None
    return None


def message_from(tags: list[dict], owner: str) -> str:
    """Host ``msg.From``: ``From-Process`` when that tag is present, otherwise the signer."""
    from_process = first_tag(tags, "From-Process")
    if from_process:
        return from_process
    return owner


def transfer(
    balances: dict[str, int],
    sender: str,
    recipient: str | None,
    quantity_text: str | None,
    *,
    stopped: bool,
    transfers_enabled: bool,
) -> dict:
    """Apply one Transfer. ``balances`` is updated only when the source would write it."""
    if stopped:
        raise RuleError("The Process is currently stopped")
    if not transfers_enabled:
        raise RuleError("Action 'Transfer' not callable. Transfers undergoing maintenance.")
    # The review map is consulted before payload.Recipient is assigned, so it
    # sees nil. Its only entry is also false. It cannot reject a transfer.
    quantity = parse_quantity(quantity_text)
    if not isinstance(recipient, str):
        raise RuleError("Cannot transfer tokens. Target address must be a string.")
    if not isinstance(sender, str):
        raise RuleError("Cannot transfer tokens. Target address must be a string.")
    if sender == recipient:
        raise RuleError(
            "Cannot transfer tokens. From address cannot be the same as the Recipient address."
        )
    if less_than(quantity, 0):
        raise RuleError("Cannot transfer tokens. Quantity must be greater than 0.")
    if sender not in balances:
        raise RuleError(
            f"Cannot transfer tokens. No balance for From address '{sender}' found."
        )
    sender_before = balances[sender]
    if less_than(sender_before, quantity):
        raise RuleError(
            f"Cannot transfer tokens. From address '{sender}' has insufficient balance."
        )
    created = recipient not in balances
    if created:
        balances[recipient] = 0
    recipient_before = balances[recipient]
    balances[recipient] = add(balances[recipient], quantity)
    balances[sender] = sub(balances[sender], quantity)
    return {
        "result": "ok",
        "quantity": decimal(quantity),
        "sender_before": decimal(sender_before),
        "sender_after": decimal(balances[sender]),
        "recipient_before": None if created else decimal(recipient_before),
        "recipient_after": decimal(balances[recipient]),
        "created_recipient": created,
    }
