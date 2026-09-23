#!/usr/bin/env python3
"""国土数値情報 N03 行政区域 (東京都) -> data/footprints.json.

One entry per municipality, keyed by its five-digit code, plus `13000` for
the whole of Tokyo. The whole of Tokyo includes 所属未定地, the islets that
belong to no municipality: they are Tokyo, and a bureau's data can be about
them.

The archive is 13 MB and is fetched once into tmp/. data/footprints.json is
small and tracked, so a build never needs the network.
"""
import argparse
import collections
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokyo_ckan_stac.footprint import merge_boxes, outer_bbox, polygon_boxes, rounded_outward  # noqa: E402
from tokyo_ckan_stac.http import UA  # noqa: E402

N03 = "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2026/N03-20260101_13_GML.zip"
PAGE = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2026.html"
GAP = 0.1  # degrees; about 10 km. Separates island groups, keeps the mainland whole.


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=GAP)
    args = ap.parse_args()

    cached = ROOT / "tmp" / N03.rsplit("/", 1)[-1]
    if not cached.exists():
        cached.parent.mkdir(exist_ok=True)
        req = urllib.request.Request(N03, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            cached.write_bytes(r.read())
    with zipfile.ZipFile(cached) as z:
        name = next(n for n in z.namelist() if n.endswith(".geojson"))
        data = json.load(io.TextIOWrapper(z.open(name), encoding="utf-8"))

    boxes, names = collections.defaultdict(list), {}
    for f in data["features"]:
        p = f["properties"]
        code = p["N03_007"]
        boxes[code] += polygon_boxes(f["geometry"])
        names[code] = p["N03_004"] if code != "13000" else "所属未定地"

    areas = {}
    for code in sorted(boxes):
        if code == "13000":
            continue
        merged = [rounded_outward(b) for b in merge_boxes(boxes[code], args.gap)]
        areas[code] = {"name": names[code], "bbox": outer_bbox(merged), "boxes": merged}
    everything = [b for v in boxes.values() for b in v]
    merged = [rounded_outward(b) for b in merge_boxes(everything, args.gap)]
    areas["13000"] = {"name": "東京都", "bbox": outer_bbox(merged), "boxes": merged}

    out = ROOT / "data" / "footprints.json"
    out.write_text(json.dumps({
        "note": "Rectangles around each municipality's polygons, from 国土数値情報 N03 行政区域. "
                f"Rectangles within {args.gap} degrees of each other are merged.",
        "source_url": N03,
        "source_page": PAGE,
        "gap_degrees": args.gap,
        "areas": areas,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(areas)} areas, {sum(len(a['boxes']) for a in areas.values())} rectangles -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
