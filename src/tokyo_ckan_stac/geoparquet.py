"""The catalog as two tables.

A question across datasets ("which wards publish a facility list with
coordinates") would otherwise mean reading 9,698 Item files. items.parquet
has one row per Item, in the stac-geoparquet manner: the fields worth
filtering on as columns, the footprint as geometry. assets.parquet has one
row per file, because a dataset here can hold 596 of them and the question
is usually about one.

The JSON stays the authoritative copy; these are indexes.
"""

from typing import Dict, List


def item_row(item: Dict, base_url: str) -> Dict:
    p = item["properties"]
    assets = item["assets"].values()
    return {
        "id": item["id"],
        "collection": item["collection"],
        "organization_title": p["tokyo:organization_title"],
        "municipality_code": p["tokyo:municipality_code"],
        "footprint_basis": p["tokyo:footprint_basis"],
        "title": p["title"],
        "description": p["description"],
        "datetime": p.get("datetime"),
        "start_datetime": p.get("start_datetime"),
        "end_datetime": p.get("end_datetime"),
        "datetime_basis": p["tokyo:datetime_basis"],
        "created": p["created"],
        "updated": p["updated"],
        "license": p["license"],
        "categories": p["tokyo:categories"],
        "formats": p["tokyo:formats"],
        "update_frequency": p["tokyo:update_frequency"],
        "update_frequency_class": p["tokyo:update_frequency_class"],
        "family": p.get("tokyo:family"),
        "family_size": p.get("tokyo:family_size"),
        "national_standard": p.get("tokyo:national_standard"),
        "family_layout_match": p.get("tokyo:family_layout_match"),
        "asset_count": len(item["assets"]),
        "datastore_count": sum(1 for a in assets if a.get("ckan:datastore_active")),
        "ckan_url": next(l["href"] for l in item["links"]
                         if l["rel"] == "via" and l.get("type") == "text/html"),
        "item_href": f"{base_url}/collections/{item['collection']}/items/{item['id']}.json",
    }


def asset_rows(item: Dict, base_url: str) -> List[Dict]:
    p = item["properties"]
    out = []
    for key, a in item["assets"].items():
        cols = a.get("table:columns")
        out.append({
            "item_id": item["id"],
            "collection": item["collection"],
            "organization_title": p["tokyo:organization_title"],
            "item_title": p["title"],
            "asset_key": key,
            "title": a.get("title"),
            "href": a["href"],
            "type": a.get("type"),
            "format": a.get("tokyo:format"),
            "ckan_format": a.get("ckan:format"),
            "start_datetime": a.get("start_datetime"),
            "end_datetime": a.get("end_datetime"),
            "created": a.get("created"),
            "ckan_size": a.get("ckan:size"),
            "datastore_active": a.get("ckan:datastore_active"),
            "columns": [c["name"] for c in cols] if cols else None,
            "row_count": a.get("table:row_count"),
            "ckan_resource_id": a.get("ckan:id"),
            "item_href": f"{base_url}/collections/{item['collection']}/items/{item['id']}.json",
        })
    return out
