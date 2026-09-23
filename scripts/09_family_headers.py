#!/usr/bin/env python3
"""The header row of every family member's first CSV -> data/headers.jsonl.

A shared name says two datasets are the same kind of thing; the columns say
whether they can be compared. Only the first 8 KiB of each file is asked for,
with a Range request, so a 30 MB CSV costs the same as a small one. A server
that ignores Range sends the whole file, and the read stops at 8 KiB anyway.

Resumable. Two workers with a pause, as for the DataStore sweep.
"""
import argparse
import json
import random
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokyo_ckan_stac.families import decode_head, families, family_name, split_header  # noqa: E402
from tokyo_ckan_stac.formats import format_label  # noqa: E402
from tokyo_ckan_stac.http import UA  # noqa: E402

OUT = ROOT / "data" / "headers.jsonl"
MIN_ORGS = 5


def first_row(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-8191"})
    with urllib.request.urlopen(req, timeout=60) as r:
        status = r.status
        blob = r.read(8192)
        ctype = r.headers.get("Content-Type", "")
    if blob.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
        raise ValueError(f"HTML instead of CSV ({ctype})")
    return status, split_header(decode_head(blob))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--min-sleep", type=float, default=1.0)
    ap.add_argument("--max-sleep", type=float, default=3.0)
    args = ap.parse_args()

    pkgs = [json.loads(l) for l in (ROOT / "data" / "packages.jsonl").open(encoding="utf-8")]
    rows = [{"family": family_name(p["title"], p["organization"]["title"]),
             "org": p["organization"]["name"], "p": p} for p in pkgs]
    fams = families(rows, MIN_ORGS)
    todo = []
    for r in rows:
        if r["family"] not in fams:
            continue
        res = sorted(r["p"]["resources"], key=lambda x: x.get("position", 0))
        csvs = [x for x in res if format_label(x.get("format"), x["url"]) == "CSV"]
        todo.append((r["p"]["name"], r["family"], csvs[0] if csvs else None))

    done = set()
    if OUT.exists():
        done = {json.loads(l)["dataset"] for l in OUT.open(encoding="utf-8") if l.strip()}
    todo = [t for t in todo if t[0] not in done]
    print(f"{len(fams)} families, {len(done)} done, {len(todo)} to go", flush=True)

    lock = threading.Lock()

    def one(t) -> None:
        name, fam, res = t
        row = {"dataset": name, "family": fam}
        if res is None:
            row["error"] = "no CSV resource"
        else:
            row["resource_id"] = res["id"]
            row["url"] = res["url"]
            time.sleep(random.uniform(args.min_sleep, args.max_sleep))
            try:
                row["status"], row["header"] = first_row(res["url"])
            except Exception as e:  # recorded, so a failure looks like one
                row["error"] = f"{type(e).__name__}: {e}"[:300]
        with lock, OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(one, todo))
    n = sum(1 for _ in OUT.open(encoding="utf-8"))
    print(f"{n} rows -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
