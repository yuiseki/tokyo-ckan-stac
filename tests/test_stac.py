import json
from pathlib import Path

from tokyo_ckan_stac.stac import build_collection, build_item, item_time

FIX = Path(__file__).parent / "fixtures"
AREAS = {
    "13103": {"name": "港区", "bbox": [139.7, 35.6, 139.8, 35.7], "boxes": [[139.7, 35.6, 139.8, 35.7]]},
    "13000": {"name": "東京都", "bbox": [136.0, 20.4, 154.0, 35.9],
              "boxes": [[138.9, 35.5, 139.9, 35.9], [136.0, 20.4, 136.1, 20.5]]},
}
BASE = "https://example.test/tokyo-ckan"


def _pkg(name):
    return json.loads((FIX / f"{name}.json").read_text())


def test_a_ward_dataset_is_placed_in_the_ward():
    it = build_item(_pkg("minato"), AREAS, BASE, "港区")
    p = it["properties"]
    assert it["bbox"] == AREAS["13103"]["bbox"]
    assert p["tokyo:footprint_basis"] == "municipality"
    assert p["tokyo:municipality_code"] == "13103"


def test_a_bureau_dataset_covers_tokyo_as_several_rectangles():
    it = build_item(_pkg("soumu"), AREAS, BASE, "東京都総務局")
    assert it["properties"]["tokyo:footprint_basis"] == "prefecture"
    assert len(it["geometry"]["coordinates"]) == 2


def test_time_comes_from_resource_names_first():
    t = item_time(_pkg("minato"))
    assert t["tokyo:datetime_basis"] == "resource-name"
    assert t["datetime"] is None
    # 2025-03-31 and 2025-04-30 in Tokyo
    assert t["start_datetime"] == "2025-03-30T15:00:00Z"
    assert t["end_datetime"] == "2025-04-30T14:59:59Z"


def test_without_dates_in_names_the_resource_created_date_is_used():
    t = item_time(_pkg("soumu"))
    assert t["tokyo:datetime_basis"] == "resource-created"
    assert t["datetime"] == "2017-07-18T06:00:00Z"


def test_the_last_resort_is_the_catalog_record():
    pkg = _pkg("soumu")
    pkg["title"] = "指定管理者"
    for r in pkg["resources"]:
        r["created"] = None
    t = item_time(pkg)
    assert t == {"datetime": pkg["metadata_created"][:19] + "Z", "tokyo:datetime_basis": "catalog-record"}


def test_the_catalog_size_is_not_passed_off_as_measured():
    it = build_item(_pkg("minato"), AREAS, BASE, "港区")
    a = it["assets"]["r000"]
    assert "file:size" not in a
    assert a["ckan:size"] == 131072


def test_assets_carry_their_own_time_and_type():
    a = build_item(_pkg("minato"), AREAS, BASE, "港区")["assets"]["r000"]
    assert a["type"] == "text/csv"
    assert a["start_datetime"] == "2025-03-30T15:00:00Z"
    assert a["roles"] == ["source"]


def test_datastore_columns_become_table_columns():
    pkg = _pkg("minato")
    rid = pkg["resources"][0]["id"]
    ds = {rid: {"fields": [{"id": "_id", "type": "int"}, {"id": "届出番号", "type": "text"}], "rows": 12}}
    it = build_item(pkg, AREAS, BASE, "港区", ds)
    a = it["assets"]["r000"]
    assert a["table:columns"] == [{"name": "届出番号", "type": "text"}]
    assert a["table:row_count"] == 12
    assert any("table" in e for e in it["stac_extensions"])


def test_links_lead_back_to_ckan():
    it = build_item(_pkg("minato"), AREAS, BASE, "港区")
    rels = {(l["rel"], l["href"]) for l in it["links"]}
    assert ("via", "https://catalog.data.metro.tokyo.lg.jp/dataset/t131032d0000000271") in rels
    assert it["links"][0]["href"] == f"{BASE}/collections/t131032/items/t131032d0000000271.json"


def test_collection_extent_spans_its_items():
    pkg = _pkg("minato")
    it = build_item(pkg, AREAS, BASE, "港区")
    c = build_collection(pkg["organization"], [it], AREAS, BASE)
    assert c["extent"]["temporal"]["interval"] == [["2025-03-30T15:00:00Z", "2025-04-30T14:59:59Z"]]
    assert c["license"] == "CC-BY-4.0"
    assert [l["href"] for l in c["links"] if l["rel"] == "item"] == ["./items/t131032d0000000271.json"]
