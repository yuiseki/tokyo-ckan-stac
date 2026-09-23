#!/usr/bin/env python3
"""data/ -> catalog/, offline.

    catalog.json
    ├── collections/catalog.json   組織別: one Collection per organisation
    │   └── <org>/collection.json, items/<dataset>.json
    ├── categories/catalog.json    分類別: category, then organisation
    ├── formats/catalog.json       形式別: format label, then organisation
    ├── items.parquet, assets.parquet   (scripts/05_geoparquet.py)
    └── README.md, AGENTS.md beside every catalog.json and collection.json

Items live only under collections/. The category and format trees link to
them; they do not copy them.
"""
import argparse
import collections
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokyo_ckan_stac.docs import node_docs, root_docs  # noqa: E402
from tokyo_ckan_stac.stac import (  # noqa: E402
    CKAN_SITE, build_catalog, build_collection, build_item)

DATA = ROOT / "data"


def write(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(doc, str):
        path.write_text(doc, encoding="utf-8")
    else:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def write_node(path: Path, doc: dict, root_rel: str) -> None:
    write(path, doc)
    readme, agents = node_docs(doc, root_rel)
    write(path.parent / "README.md", readme)
    write(path.parent / "AGENTS.md", agents)


def load_datastore():
    path = DATA / "datastore.jsonl"
    if not path.exists():
        return {}, 0
    out, errors = {}, 0
    for line in path.open(encoding="utf-8"):
        row = json.loads(line)
        if "error" in row:
            errors += 1
            continue
        out[row["resource_id"]] = row
    return out, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://stac.yuiseki.net/tokyo-ckan")
    ap.add_argument("--out", default=str(ROOT / "catalog"))
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    out = Path(args.out)

    pkgs = [json.loads(l) for l in (DATA / "packages.jsonl").open(encoding="utf-8")]
    areas = json.loads((DATA / "footprints.json").read_text())["areas"]
    datastore, ds_errors = load_datastore()
    print(f"{len(pkgs)} datasets, {len(datastore)} DataStore schemas ({ds_errors} failed)")

    if out.exists():
        shutil.rmtree(out)

    by_org = collections.defaultdict(list)
    orgs = {}
    for p in pkgs:
        orgs[p["organization"]["name"]] = p["organization"]
        by_org[p["organization"]["name"]].append(p)

    all_items, colls = [], {}
    for oid in sorted(by_org):
        org = orgs[oid]
        items = [build_item(p, areas, base, org["title"], datastore) for p in by_org[oid]]
        coll = build_collection(org, items, areas, base)
        colls[oid] = coll
        cdir = out / "collections" / oid
        for it in items:
            write(cdir / "items" / f"{it['id']}.json", it)
        write_node(cdir / "collection.json", coll, "../../")
        all_items += items

    # 組織別
    children = [{"href": f"./{oid}/collection.json",
                 "title": f"{c['title']} ({c['tokyo:item_count']})"} for oid, c in
                sorted(colls.items(), key=lambda kv: -kv[1]["tokyo:item_count"])]
    write_node(out / "collections" / "catalog.json", build_catalog(
        "organisations", "組織別 (by organisation)",
        f"{len(colls)} の組織。都の局と区市町村。件数の多い順。",
        f"{base}/collections/catalog.json", "../catalog.json", "../catalog.json", "東京都オープンデータカタログ",
        children), "../")

    # Two browse trees with the same shape: axis value, then organisation.
    axes = {
        "categories": ("分類別 (by category)", "tokyo:categories",
                       "CKAN のグループ(分類)。1 つのデータセットが複数の分類に属することがある。"),
        "formats": ("形式別 (by format)", "tokyo:formats",
                    "公開者が付けた形式ラベル(正規化済み)。1 つのデータセットが複数の形式を持つことがある。"),
    }
    group_ids = {g["title"]: g["name"] for p in pkgs for g in p.get("groups") or []}
    for axis, (title, prop, desc) in axes.items():
        index = collections.defaultdict(lambda: collections.defaultdict(list))
        for it in all_items:
            for v in it["properties"][prop]:
                index[v][it["collection"]].append(it)
        axis_children = []
        for value in sorted(index, key=lambda v: -sum(len(x) for x in index[v].values())):
            slug = group_ids.get(value, value) if axis == "categories" else value.lower()
            vdir = out / axis / slug
            total = sum(len(x) for x in index[value].values())
            org_children = []
            for oid in sorted(index[value], key=lambda o: -len(index[value][o])):
                its = sorted(index[value][oid], key=lambda i: (i["properties"]["title"], i["id"]))
                write_node(vdir / oid / "catalog.json", build_catalog(
                    f"{axis}-{slug}-{oid}", f"{value} / {orgs[oid]['title']}",
                    f"{orgs[oid]['title']} の「{value}」のデータセット {len(its)} 件。",
                    f"{base}/{axis}/{slug}/{oid}/catalog.json", "../../../catalog.json",
                    "../catalog.json", value, [],
                    [{"href": f"../../../collections/{oid}/items/{i['id']}.json",
                      "title": i["properties"]["title"]} for i in its]), "../../../")
                org_children.append({"href": f"./{oid}/catalog.json",
                                     "title": f"{orgs[oid]['title']} ({len(its)})"})
            extra = []
            if axis == "categories" and value in group_ids:
                extra = [{"rel": "via", "href": f"{CKAN_SITE}/group/{group_ids[value]}",
                          "type": "text/html", "title": "東京都オープンデータカタログの分類ページ"}]
            write_node(vdir / "catalog.json", build_catalog(
                f"{axis}-{slug}", value, f"「{value}」のデータセット {total} 件を組織別に。",
                f"{base}/{axis}/{slug}/catalog.json", "../../catalog.json", "../catalog.json", title,
                org_children, extra_links=extra), "../../")
            axis_children.append({"href": f"./{slug}/catalog.json", "title": f"{value} ({total})"})
        write_node(out / axis / "catalog.json", build_catalog(
            axis, title, desc, f"{base}/{axis}/catalog.json", "../catalog.json", "../catalog.json",
            "東京都オープンデータカタログ", axis_children), "../")

    # collections/index.json: every Collection with its description, in one file.
    write(out / "collections" / "index.json", [
        {"id": c["id"], "title": c["title"], "items": c["tokyo:item_count"],
         "footprint_basis": c["tokyo:footprint_basis"], "categories": c["keywords"],
         "href": f"./{c['id']}/collection.json"}
        for c in sorted(colls.values(), key=lambda c: -c["tokyo:item_count"])])

    stats = {
        "datasets": len(all_items),
        "resources": sum(len(i["assets"]) for i in all_items),
        "organisations": len(colls),
        "datastore_schemas": len(datastore),
        "basis": collections.Counter(i["properties"]["tokyo:datetime_basis"] for i in all_items),
        "footprint": collections.Counter(i["properties"]["tokyo:footprint_basis"] for i in all_items),
        "licenses": collections.Counter(i["properties"]["license"] for i in all_items),
    }
    root = build_catalog(
        "tokyo-ckan", "東京都オープンデータカタログ (Tokyo Open Data Catalog)",
        f"東京都オープンデータカタログ (CKAN) の {stats['datasets']} データセット、"
        f"{stats['resources']} ファイルを static STAC にしたもの。非公式のミラーで、データ本体は持たず公開元へリンクする。",
        f"{base}/catalog.json", "./catalog.json", None, None,
        [{"href": "./collections/catalog.json", "title": "組織別 (by organisation)"},
         {"href": "./categories/catalog.json", "title": "分類別 (by category)"},
         {"href": "./formats/catalog.json", "title": "形式別 (by format)"}],
        extra_links=[
            {"rel": "via", "href": CKAN_SITE, "type": "text/html", "title": "東京都オープンデータカタログ"},
            {"rel": "alternate", "href": "./collections/index.json", "type": "application/json",
             "title": "collections/index.json: 全組織の一覧"},
            {"rel": "alternate", "href": "./items.parquet", "type": "application/vnd.apache.parquet",
             "title": "items.parquet: 全データセットを 1 つの GeoParquet に"},
            {"rel": "alternate", "href": "./assets.parquet", "type": "application/vnd.apache.parquet",
             "title": "assets.parquet: 全ファイルを 1 行ずつ"},
        ])
    write(out / "catalog.json", root)
    readme, agents = root_docs(stats, base)
    write(out / "README.md", readme)
    write(out / "AGENTS.md", agents)

    print(f"{stats['datasets']} items, {stats['resources']} assets, {len(colls)} collections -> {out}")
    print(f"  datetime basis: {dict(stats['basis'])}")
    print(f"  footprint basis: {dict(stats['footprint'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
