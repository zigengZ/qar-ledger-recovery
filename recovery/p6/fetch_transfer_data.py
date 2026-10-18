#!/usr/bin/env python3
"""Fetch /raw and /tx for the five GraphQL data.size=0 Transfer messages.

Saves the request, response headers, and body for each gateway. Does not
follow the old https://<gateway>/<id> HTML path. Concurrency is 4.
"""
import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RAW = Path(__file__).resolve().parents[2] / "data/raw/eval" / f"{RUN}-w-eval"
OUT = RAW / "http"

TRANSFERS = [
    {
        "id": "4abmavZXf81Y-UheWFraPxmUubZni_XgdmF_tckrg9Y",
        "nonce": 2074509,
        "quantity": "940193118330",
        "recipient": "wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4",
        "xArbId": "50174802552002569a0f",
    },
    {
        "id": "ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw",
        "nonce": 2074511,
        "quantity": "189406046916",
        "recipient": "wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4",
        "xArbId": "5017507420314260bc9e",
    },
    {
        "id": "iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY",
        "nonce": 2074513,
        "quantity": "822375701087",
        "recipient": "wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4",
        "xArbId": "50175075674982619df4",
    },
    {
        "id": "0EA0BJGA2eP79w5Zply6VYuEop7SMrYkuzo_tCYdIYw",
        "nonce": 2074515,
        "quantity": "2009265632204",
        "recipient": "wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4",
        "xArbId": "5017512925894264115e",
    },
    {
        "id": "OZYnrr04Q8WU9Fr-GNDcnm407F-jM0MSC6EdgSgaL8Q",
        "nonce": 2074517,
        "quantity": "576448605054",
        "recipient": "wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4",
        "xArbId": "50175229301722660007",
    },
]

GATEWAYS = ["https://arweave.net", "https://ar-io.dev"]
KINDS = ["raw", "tx"]


def sha256(buf):
    return hashlib.sha256(buf).hexdigest()


def fetch_one(gateway, kind, item):
    url = f"{gateway}/{kind}/{item['id']}"
    dest = OUT / gateway.removeprefix("https://") / kind
    dest.mkdir(parents=True, exist_ok=True)
    stem = dest / item["id"]
    request = {
        "method": "GET",
        "url": url,
        "gateway": gateway,
        "kind": kind,
        "id": item["id"],
        "nonce": item["nonce"],
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    stem.with_suffix(".request.json").write_text(json.dumps(request, indent=2) + "\n")
    header_path = stem.with_name(item["id"] + ".headers")
    body_path = stem.with_name(item["id"] + ".body")
    meta = dict(request)
    delay = 2
    for attempt in range(1, 4):
        started = time.time()
        proc = subprocess.run(
            [
                "curl", "-sS", "-L", "--max-redirs", "3", "--max-time", "60",
                "-D", str(header_path),
                "-o", str(body_path),
                "-A", "qar-ledger-recovery",
                "-w", "%{http_code} %{size_download} %{num_redirects}",
                url,
            ],
            capture_output=True,
            text=True,
        )
        meta["attempt"] = attempt
        meta["curlExit"] = proc.returncode
        meta["curlStderr"] = proc.stderr[-500:]
        meta["curlWriteOut"] = proc.stdout.strip()
        meta["elapsedMs"] = int((time.time() - started) * 1000)
        code = proc.stdout.split()[0] if proc.stdout else ""
        if proc.returncode == 0 and code not in {"429", "500", "502", "503", "504"}:
            break
        meta.setdefault("retries", []).append({"attempt": attempt, "code": code, "stderr": proc.stderr[-300:]})
        time.sleep(delay)
        delay *= 2
    body = body_path.read_bytes() if body_path.exists() else b""
    headers = header_path.read_text(errors="replace") if header_path.exists() else ""
    meta["bodyBytes"] = len(body)
    meta["bodySha256"] = sha256(body)
    meta["bodyEmpty"] = len(body) == 0
    meta["bodyStartsWithHtml"] = body[:15].lower().startswith(b"<!doctype html") or body[:6].lower().startswith(b"<html")
    meta["headerStatusLines"] = [line for line in headers.splitlines() if line.startswith("HTTP/")]
    content_type = ""
    for line in headers.splitlines():
        if line.lower().startswith("content-type:"):
            content_type = line.split(":", 1)[1].strip()
    meta["lastContentType"] = content_type
    if kind == "tx" and body[:1] in (b"{", b"["):
        try:
            doc = json.loads(body)
            meta["tx"] = {
                "data_size": doc.get("data_size"),
                "dataFieldBytes": len(doc.get("data") or ""),
                "dataFieldEmpty": (doc.get("data") or "") == "",
                "format": doc.get("format"),
                "id": doc.get("id"),
                "target": doc.get("target"),
                "tags": doc.get("tags"),
            }
        except json.JSONDecodeError as error:
            meta["txParseError"] = str(error)
    stem.with_name(item["id"] + ".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({
        "gateway": gateway,
        "kind": kind,
        "id": item["id"],
        "nonce": item["nonce"],
        "status": meta["headerStatusLines"],
        "bytes": meta["bodyBytes"],
        "empty": meta["bodyEmpty"],
        "html": meta["bodyStartsWithHtml"],
        "tx": meta.get("tx", {}).get("data_size") if "tx" in meta else None,
        "exit": proc.returncode,
    }, ensure_ascii=False), flush=True)
    return meta


def fetch_sequential(url, dest_stem):
    """One GET. Writes request, headers, and body next to dest_stem. Sleeps before return."""
    dest_stem.parent.mkdir(parents=True, exist_ok=True)
    request = {
        "method": "GET",
        "url": url,
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    Path(str(dest_stem) + ".request.json").write_text(json.dumps(request, indent=2) + "\n")
    header_path = Path(str(dest_stem) + ".headers")
    body_path = Path(str(dest_stem) + ".body")
    proc = subprocess.run(
        [
            "curl", "-sS", "-L", "--max-redirs", "3", "--max-time", "90",
            "-D", str(header_path),
            "-o", str(body_path),
            "-A", "qar-ledger-recovery",
            "-w", "%{http_code} %{size_download} %{num_redirects}",
            url,
        ],
        capture_output=True,
        text=True,
    )
    body = body_path.read_bytes() if body_path.exists() else b""
    headers = header_path.read_text(errors="replace") if header_path.exists() else ""
    meta = dict(request)
    meta.update({
        "curlExit": proc.returncode,
        "curlStderr": proc.stderr[-500:],
        "curlWriteOut": proc.stdout.strip(),
        "bodyBytes": len(body),
        "bodySha256": sha256(body),
        "bodyEmpty": len(body) == 0,
        "headerStatusLines": [line for line in headers.splitlines() if line.startswith("HTTP/")],
    })
    Path(str(dest_stem) + ".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"url": url, "status": meta["headerStatusLines"], "bytes": len(body), "exit": proc.returncode}, ensure_ascii=False), flush=True)
    time.sleep(3)
    return meta


def sequential_fill(run):
    """Slow second pass. Does not overwrite the first-pass bodies."""
    raw = Path(__file__).resolve().parents[2] / "data/raw/eval" / f"{run}-w-eval/http"
    retry_ids = [
        "ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw",
        "iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY",
    ]
    for txid in retry_ids:
        fetch_sequential(
            f"https://arweave.net/raw/{txid}",
            raw / "arweave.net" / "raw" / f"{txid}.retry",
        )
    turbo_raw_ok = []
    for item in TRANSFERS:
        meta = fetch_sequential(
            f"https://turbo-gateway.com/raw/{item['id']}",
            raw / "turbo-gateway.com" / "raw" / item["id"],
        )
        status = " ".join(meta["headerStatusLines"])
        turbo_raw_ok.append("200" in status and meta["bodyEmpty"])
    for item in TRANSFERS:
        fetch_sequential(
            f"https://turbo-gateway.com/tx/{item['id']}",
            raw / "turbo-gateway.com" / "tx" / item["id"],
        )
    # A second data gateway is required. Use vilenarios when turbo did not
    # return an empty 200 for every raw body.
    if not all(turbo_raw_ok):
        for kind in ("raw", "tx"):
            for item in TRANSFERS:
                fetch_sequential(
                    f"https://vilenarios.com/{kind}/{item['id']}",
                    raw / "vilenarios.com" / kind / item["id"],
                )


def main():
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--sequential":
        sequential_fill(sys.argv[2])
        return
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(gateway, kind, item) for gateway in GATEWAYS for kind in KINDS for item in TRANSFERS]
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch_one, gateway, kind, item) for gateway, kind, item in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    summary = {"run": RUN, "raw": str(RAW), "results": results}
    (RAW / "fetch-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("RUN", RUN)


if __name__ == "__main__":
    main()
