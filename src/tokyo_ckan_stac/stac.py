"""CKAN records -> STAC documents.

One CKAN organisation is one Collection, one dataset is one Item, and one
resource is one asset. The functions here are pure: they take records and
return dicts, and the build script decides where the files go.

Nothing here invents a value CKAN does not have. Where a STAC field is
required and CKAN has nothing that answers it, the value is derived and the
derivation is named beside it: `tokyo:datetime_basis` for time,
`tokyo:footprint_basis` for place.
"""

from typing import Dict, List, Optional

from .dates import ckan_instant, intervals_in, span
from .footprint import geometry_of
from .formats import format_label, media_type
from .freq import frequency_class
from .lgcode import municipality_code

STAC_VERSION = "1.1.0"
TABLE_EXT = "https://stac-extensions.github.io/table/v1.2.0/schema.json"
FILE_EXT = "https://stac-extensions.github.io/file/v2.1.0/schema.json"
CKAN_SITE = "https://catalog.data.metro.tokyo.lg.jp"
ROOT_TITLE = "東京都オープンデータカタログ (Tokyo Open Data Catalog)"
HOST = {
    "name": "東京都オープンデータカタログ",
    "roles": ["host"],
    "url": CKAN_SITE,
}

J = "application/json"
GJ = "application/geo+json"


def extra(pkg: Dict, key: str) -> Optional[str]:
    for e in pkg.get("extras") or []:
        if e.get("key") == key:
            return e.get("value")
    return None


def footprint_key(pkg: Dict) -> str:
    """The N03 area a dataset's publisher is responsible for."""
    return municipality_code(pkg["organization"]["name"]) or "13000"


def item_time(pkg: Dict) -> Dict:
    """datetime or start/end, and which evidence they came from.

    In order: dates in the resource names; dates in the dataset title; the
    `created` date the publisher gave each resource; when the dataset record
    was created in the catalog. The first that yields anything wins.
    """
    names = [r.get("name") or "" for r in pkg["resources"]]
    for basis, texts in (("resource-name", names), ("dataset-title", [pkg.get("title") or ""])):
        found = [iv for t in texts for iv in intervals_in(t)]
        if found:
            start, end = span(found)
            return {"datetime": None, "start_datetime": start, "end_datetime": end,
                    "tokyo:datetime_basis": basis}
    created = sorted(filter(None, (ckan_instant(r.get("created")) for r in pkg["resources"])))
    if created:
        if created[0] == created[-1]:
            return {"datetime": created[0], "tokyo:datetime_basis": "resource-created"}
        return {"datetime": None, "start_datetime": created[0], "end_datetime": created[-1],
                "tokyo:datetime_basis": "resource-created"}
    return {"datetime": ckan_instant(pkg["metadata_created"]), "tokyo:datetime_basis": "catalog-record"}


def asset_of(res: Dict, columns: Optional[Dict]) -> Dict:
    a = {"href": res["url"], "title": res.get("name") or res["url"].rsplit("/", 1)[-1],
         "roles": ["source"]}
    t = media_type(res.get("format"), res["url"])
    if t:
        a["type"] = t
    if res.get("description") and res["description"] != res.get("name"):
        a["description"] = res["description"]
    label = format_label(res.get("format"), res["url"])
    if label:
        a["tokyo:format"] = label
    if res.get("format"):
        a["ckan:format"] = res["format"]
    iv = intervals_in(res.get("name") or "")
    if iv:
        a["start_datetime"], a["end_datetime"] = span(iv)
    if res.get("created"):
        a["created"] = ckan_instant(res["created"])
    if res.get("size") is not None:
        # The catalog's own figure, rounded down to a KiB and sometimes 1.
        # file:size is reserved for a measured Content-Length.
        a["ckan:size"] = res["size"]
    a["ckan:id"] = res["id"]
    a["ckan:datastore_active"] = bool(res.get("datastore_active"))
    if columns and columns.get("fields"):
        a["table:columns"] = [
            {"name": f["id"], "type": f.get("type")} for f in columns["fields"] if f["id"] != "_id"]
        if columns.get("rows") is not None:
            a["table:row_count"] = columns["rows"]
    return a


def asset_key(res: Dict) -> str:
    return f"r{res.get('position', 0):03d}"


def build_item(pkg: Dict, areas: Dict, base_url: str, collection_title: str,
               datastore: Optional[Dict] = None) -> Dict:
    datastore = datastore or {}
    org = pkg["organization"]
    key = footprint_key(pkg)
    area = areas[key]
    freq = extra(pkg, "更新頻度")
    groups = [g["title"] for g in pkg.get("groups") or []]
    assets = {}
    for res in sorted(pkg["resources"], key=lambda r: r.get("position", 0)):
        assets[asset_key(res)] = asset_of(res, datastore.get(res["id"]))
    formats = sorted({a["tokyo:format"] for a in assets.values() if "tokyo:format" in a})

    props = {
        "title": pkg["title"],
        "description": (pkg.get("notes") or pkg["title"]).strip(),
        **item_time(pkg),
        "created": ckan_instant(pkg["metadata_created"]),
        "updated": ckan_instant(pkg["metadata_modified"]),
        "license": pkg.get("license_id") or "other",
        "providers": [
            {"name": org["title"], "roles": ["producer", "licensor"],
             **({"url": org["description"]} if (org.get("description") or "").startswith("http") else {})},
            HOST,
        ],
        "keywords": [t["name"] for t in pkg.get("tags") or []],
        "tokyo:organization": org["name"],
        "tokyo:organization_title": org["title"],
        "tokyo:municipality_code": municipality_code(org["name"]),
        "tokyo:footprint_basis": "municipality" if key != "13000" else "prefecture",
        "tokyo:footprint_area": area["name"],
        "tokyo:categories": groups,
        "tokyo:formats": formats,
        "tokyo:update_frequency": freq,
        "tokyo:update_frequency_class": frequency_class(freq),
        "ckan:id": pkg["id"],
        "ckan:name": pkg["name"],
    }
    if pkg.get("maintainer"):
        props["tokyo:maintainer"] = pkg["maintainer"]
    if not props["keywords"]:
        del props["keywords"]

    cid = org["name"]
    links = [
        {"rel": "self", "href": f"{base_url}/collections/{cid}/items/{pkg['name']}.json", "type": GJ},
        {"rel": "root", "href": "../../../catalog.json", "type": J, "title": ROOT_TITLE},
        {"rel": "parent", "href": "../collection.json", "type": J, "title": collection_title},
        {"rel": "collection", "href": "../collection.json", "type": J, "title": collection_title},
        {"rel": "via", "href": f"{CKAN_SITE}/dataset/{pkg['name']}", "type": "text/html",
         "title": "東京都オープンデータカタログのデータセットページ"},
        {"rel": "via", "href": f"{CKAN_SITE}/api/3/action/package_show?id={pkg['name']}", "type": J,
         "title": "CKAN package_show"},
    ]
    if pkg.get("url"):
        links.append({"rel": "related", "href": pkg["url"], "type": "text/html",
                      "title": "公開元のページ"})
    if pkg.get("license_url"):
        links.append({"rel": "license", "href": pkg["license_url"], "type": "text/html",
                      "title": pkg.get("license_title") or pkg.get("license_id")})

    exts = []
    if any("table:columns" in a for a in assets.values()):
        exts.append(TABLE_EXT)
    return {
        "type": "Feature",
        "stac_version": STAC_VERSION,
        "stac_extensions": exts,
        "id": pkg["name"],
        "collection": cid,
        "geometry": geometry_of(area["boxes"]),
        "bbox": area["bbox"],
        "properties": props,
        "links": links,
        "assets": assets,
    }


def time_bounds(items: List[Dict]) -> List[Optional[str]]:
    starts, ends = [], []
    for it in items:
        p = it["properties"]
        starts.append(p.get("start_datetime") or p["datetime"])
        ends.append(p.get("end_datetime") or p["datetime"])
    return [min(starts), max(ends)] if items else [None, None]


def collection_license(items: List[Dict]) -> str:
    ids = {it["properties"]["license"] for it in items}
    return ids.pop() if len(ids) == 1 else "other"


def build_collection(org: Dict, items: List[Dict], areas: Dict, base_url: str) -> Dict:
    cid = org["name"]
    key = municipality_code(cid) or "13000"
    area = areas[key]
    cats: Dict[str, int] = {}
    fmts: Dict[str, int] = {}
    for it in items:
        for c in it["properties"]["tokyo:categories"]:
            cats[c] = cats.get(c, 0) + 1
        for f in it["properties"]["tokyo:formats"]:
            fmts[f] = fmts.get(f, 0) + 1
    desc = f"{org['title']} が東京都オープンデータカタログで公開している {len(items)} 件のデータセット。"
    if (org.get("description") or "").startswith("http"):
        desc += f" 公開元: {org['description']}"
    lic = collection_license(items)
    links = [
        {"rel": "self", "href": f"{base_url}/collections/{cid}/collection.json", "type": J},
        {"rel": "root", "href": "../../catalog.json", "type": J, "title": ROOT_TITLE},
        {"rel": "parent", "href": "../catalog.json", "type": J, "title": "組織別 (by organisation)"},
        {"rel": "via", "href": f"{CKAN_SITE}/organization/{cid}", "type": "text/html",
         "title": "東京都オープンデータカタログの組織ページ"},
        {"rel": "describedby", "href": "./README.md", "type": "text/markdown", "title": "README"},
        {"rel": "agents", "href": "./AGENTS.md", "type": "text/markdown",
         "title": "AGENTS.md: how to get an answer out of this catalog"},
    ]
    for url, title in sorted({(l["href"], l.get("title")) for it in items for l in it["links"]
                              if l["rel"] == "license"}):
        links.append({"rel": "license", "href": url, "type": "text/html", "title": title})
    for it in sorted(items, key=lambda i: (i["properties"]["title"], i["id"])):
        links.append({"rel": "item", "href": f"./items/{it['id']}.json", "type": GJ,
                      "title": it["properties"]["title"]})
    return {
        "type": "Collection",
        "stac_version": STAC_VERSION,
        "stac_extensions": [],
        "id": cid,
        "title": org["title"],
        "description": desc,
        "keywords": sorted(cats, key=lambda c: -cats[c]),
        "license": lic,
        "providers": items[0]["properties"]["providers"] if items else [HOST],
        "extent": {
            "spatial": {"bbox": [area["bbox"], *area["boxes"]] if len(area["boxes"]) > 1 else [area["bbox"]]},
            "temporal": {"interval": [time_bounds(items)]},
        },
        "summaries": {
            "tokyo:categories": sorted(cats),
            "tokyo:formats": sorted(fmts),
        },
        "tokyo:footprint_basis": "municipality" if key != "13000" else "prefecture",
        "tokyo:item_count": len(items),
        "links": links,
    }


def build_catalog(cid: str, title: str, description: str, self_href: str, root_href: str,
                  parent_href: Optional[str], parent_title: Optional[str],
                  children: List[Dict], items: List[Dict] = (), extra_links: List[Dict] = ()) -> Dict:
    """A plain Catalog. `children` and `items` are link dicts with href and title."""
    links = [
        {"rel": "self", "href": self_href, "type": J},
        {"rel": "root", "href": root_href, "type": J, "title": ROOT_TITLE},
    ]
    if parent_href:
        links.append({"rel": "parent", "href": parent_href, "type": J, "title": parent_title})
    links += [
        {"rel": "describedby", "href": "./README.md", "type": "text/markdown", "title": "README"},
        {"rel": "agents", "href": "./AGENTS.md", "type": "text/markdown",
         "title": "AGENTS.md: how to get an answer out of this catalog"},
        *extra_links,
    ]
    links += [{"rel": "child", "type": J, **c} for c in children]
    links += [{"rel": "item", "type": GJ, **i} for i in items]
    return {"type": "Catalog", "stac_version": STAC_VERSION, "id": cid, "title": title,
            "description": description, "links": links}
