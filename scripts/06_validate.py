#!/usr/bin/env python3
"""Checks that hold whether or not a STAC validator is installed.

The rules here are the ones this catalog can get wrong on its own: a time
without its basis, a size that was copied from CKAN and called measured, a
link that points at a file that is not there. If `stac-validator` is
available it runs as well, against the schemas, on a sample.
"""
import collections
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASES = {"resource-name", "dataset-title", "resource-created", "catalog-record"}


def _validator_cmd():
    if shutil.which("stac-validator"):
        return ["stac-validator"]
    if shutil.which("uvx"):
        return ["uvx", "--quiet", "--from", "stac-valid", "stac-validator"]
    return None


def main() -> int:
    cat = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "catalog"
    if not (cat / "catalog.json").exists():
        print(f"no catalog at {cat}. Run `make build` first.", file=sys.stderr)
        return 1

    errors, notes = [], collections.Counter()
    items = sorted(cat.glob("collections/*/items/*.json"))
    for p in items:
        d = json.loads(p.read_text())
        rel = p.relative_to(cat)
        props = d["properties"]
        if (d.get("geometry") is None) != ("bbox" not in d):
            errors.append(f"{rel}: geometry and bbox disagree about existing")
        if props.get("datetime") is None and not (props.get("start_datetime") and props.get("end_datetime")):
            errors.append(f"{rel}: datetime is null without an interval")
        if props.get("tokyo:datetime_basis") not in BASES:
            errors.append(f"{rel}: time without a known basis")
        if props.get("tokyo:footprint_basis") not in ("municipality", "prefecture"):
            errors.append(f"{rel}: footprint without a basis")
        s, e = props.get("start_datetime"), props.get("end_datetime")
        if s and e and s > e:
            errors.append(f"{rel}: start_datetime after end_datetime")
        for name, a in d["assets"].items():
            if not a.get("roles"):
                errors.append(f"{rel}: asset {name} has no role")
            if "file:size" in a:
                errors.append(f"{rel}: asset {name} claims a measured size nothing measured")
            if not a.get("type"):
                notes["asset without a media type"] += 1

    # Every relative link in every document, whatever its rel.
    for p in sorted(cat.rglob("*.json")):
        d = json.loads(p.read_text())
        if not isinstance(d, dict):
            continue
        rel = p.relative_to(cat)
        for link in d.get("links", []):
            href = link.get("href", "")
            if not href or href.startswith(("http://", "https://")):
                continue
            if not (p.parent / href).resolve().exists():
                errors.append(f"{rel}: dangling {link['rel']} link: {href}")
            if link["rel"] in ("item", "child") and not link.get("title"):
                errors.append(f"{rel}: {link['rel']} link without a title: {href}")
        if d.get("type") in ("Catalog", "Collection"):
            rels = {l.get("rel") for l in d.get("links", [])}
            for fname, want in (("README.md", "describedby"), ("AGENTS.md", "agents")):
                if not (p.parent / fname).exists():
                    errors.append(f"{rel}: no {fname} beside it")
                if want not in rels:
                    errors.append(f"{rel}: no rel={want} link")

    print(f"{len(items)} items checked")
    for k, v in notes.items():
        print(f"  note: {v} {k}")
    for e in errors[:40]:
        print(f"  {e}")
    if len(errors) > 40:
        print(f"  ... and {len(errors) - 40} more")

    cmd = _validator_cmd()
    if cmd:
        samples = [cat / "catalog.json", cat / "collections" / "catalog.json",
                   next(iter(sorted(cat.glob("collections/*/collection.json")))),
                   next(iter(sorted(cat.glob("categories/*/*/catalog.json"))))]
        # One item of each shape: with and without table:columns, each time basis.
        seen = set()
        for p in items:
            d = json.loads(p.read_text())
            key = (d["properties"]["tokyo:datetime_basis"], bool(d["stac_extensions"]),
                   d["properties"]["tokyo:footprint_basis"])
            if key not in seen:
                seen.add(key)
                samples.append(p)
        for sample in samples:
            r = subprocess.run([*cmd, "validate", str(sample)], capture_output=True, text=True)
            ok = '"valid_stac": true' in r.stdout
            print(f"  {'ok  ' if ok else 'FAIL'} {sample.relative_to(cat)}")
            if not ok:
                print((r.stdout or r.stderr)[-2000:])
                errors.append(f"{sample.relative_to(cat)}: schema validation failed")
    else:
        print("no STAC schema validator found; install stac-valid or put uv on PATH")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
