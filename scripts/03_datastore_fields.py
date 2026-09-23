#!/usr/bin/env python3
"""Column names and types of every DataStore resource -> data/datastore.jsonl.

When a CSV or spreadsheet was loaded into the DataStore, CKAN knows its
columns. That is the only schema information the catalog has, and it is what
lets a reader decide whether a table is worth downloading.

Resumable: resources already in the output are skipped. Two workers and a
random pause keep this to about one request a second against a service the
metropolitan government runs for everyone.
"""
import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokyo_ckan_stac.http import action  # noqa: E402

OUT = ROOT / "data" / "datastore.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--min-sleep", type=float, default=1.0)
    ap.add_argument("--max-sleep", type=float, default=3.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    todo = []
    for line in (ROOT / "data" / "packages.jsonl").open(encoding="utf-8"):
        p = json.loads(line)
        todo += [r["id"] for r in p["resources"] if r.get("datastore_active")]
    done = set()
    if OUT.exists():
        done = {json.loads(l)["resource_id"] for l in OUT.open(encoding="utf-8") if l.strip()}
    todo = [r for r in todo if r not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)

    lock, count = threading.Lock(), {"n": 0, "err": 0}

    def one(rid: str) -> None:
        time.sleep(random.uniform(args.min_sleep, args.max_sleep))
        try:
            res = action("datastore_info", id=rid, timeout=60)
            row = {
                "resource_id": rid,
                "fields": [{"id": f["id"], "type": f.get("type")} for f in res.get("fields", [])],
                "rows": (res.get("meta") or {}).get("count"),
            }
        except Exception as e:  # recorded, so a failure looks like one
            row = {"resource_id": rid, "error": f"{type(e).__name__}: {e}"[:300]}
        with lock:
            with OUT.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count["n"] += 1
            count["err"] += "error" in row
            if count["n"] % 200 == 0:
                print(f"  {count['n']} / {len(todo)}  errors {count['err']}", flush=True)

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(one, todo))
    print(f"{count['n']} fetched, {count['err']} errors -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
