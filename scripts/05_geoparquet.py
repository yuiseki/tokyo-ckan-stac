#!/usr/bin/env python3
"""catalog/ -> catalog/items.parquet and catalog/assets.parquet.

Offline. Reads the JSON that 04_build_stac.py wrote, so the tables and the
tree cannot disagree except by being built at different times.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokyo_ckan_stac.geoparquet import asset_rows, item_row  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    ap.add_argument("--base-url", default="https://stac.yuiseki.net/tokyo-ckan")
    args = ap.parse_args()

    import geopandas as gpd  # noqa: PLC0415
    import pandas as pd  # noqa: PLC0415
    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.parquet as pq  # noqa: PLC0415
    from shapely.geometry import shape  # noqa: PLC0415

    cat = Path(args.catalog)
    base = args.base_url.rstrip("/")
    rows, arows, geoms = [], [], []
    for p in sorted(cat.glob("collections/*/items/*.json")):
        d = json.loads(p.read_text())
        rows.append(item_row(d, base))
        arows += asset_rows(d, base)
        geoms.append(shape(d["geometry"]))

    gdf = gpd.GeoDataFrame(rows, geometry=gpd.GeoSeries(geoms, crs="EPSG:4326"))
    # Near in space, near in the file, so a reader asking about one ward can
    # skip most row groups.
    gdf["_h"] = gdf.geometry.hilbert_distance()
    gdf = gdf.sort_values(["_h", "id"]).drop(columns="_h").reset_index(drop=True)
    out = cat / "items.parquet"
    gdf.to_parquet(out, compression="zstd", write_covering_bbox=True,
                   schema_version="1.1.0", row_group_size=2000)

    adf = pd.DataFrame(arows)
    aout = cat / "assets.parquet"
    pq.write_table(pa.Table.from_pandas(adf, preserve_index=False), aout,
                   compression="zstd", row_group_size=20000)

    back = gpd.read_parquet(out)
    aback = pq.read_table(aout)
    assert len(back) == len(rows), "item rows changed on the way to Parquet"
    assert aback.num_rows == len(arows), "asset rows changed on the way to Parquet"
    print(f"{len(back)} items, {out.stat().st_size / 1024**2:.1f} MB -> {out}")
    print(f"{aback.num_rows} assets, {aout.stat().st_size / 1024**2:.1f} MB -> {aout}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
