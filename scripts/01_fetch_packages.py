#!/usr/bin/env python3
"""Every dataset in the catalog -> data/packages.jsonl.

package_search returns whole records, resources included, 1,000 at a time,
so the entire catalog is ten requests. Paging is by name so that a dataset
added while this runs cannot shift another one across a page boundary
unseen; the count is checked against the total at the end either way.
"""
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokyo_ckan_stac.http import action  # noqa: E402

ROWS = 1000


def main() -> int:
    out, total, start = [], None, 0
    while total is None or start < total:
        res = action("package_search", rows=ROWS, start=start, sort="name asc")
        total = res["count"]
        out.extend(res["results"])
        print(f"  {len(out):>5} / {total}", flush=True)
        start += ROWS
        time.sleep(random.uniform(2, 6))

    ids = {p["id"] for p in out}
    if len(ids) != len(out) or len(out) != total:
        print(f"expected {total} datasets, got {len(out)} rows and {len(ids)} ids; "
              "the catalog changed while paging. Run again.", file=sys.stderr)
        return 1

    path = ROOT / "data" / "packages.jsonl"
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for p in out:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    tmp.replace(path)
    print(f"{len(out)} datasets, {sum(len(p['resources']) for p in out)} resources -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
