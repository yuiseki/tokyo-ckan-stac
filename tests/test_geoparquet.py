from tokyo_ckan_stac.geoparquet import asset_rows, item_row
from tokyo_ckan_stac.stac import build_item

from test_stac import AREAS, BASE, _pkg


def test_one_row_per_item_with_the_bases_beside_the_values():
    it = build_item(_pkg("minato"), AREAS, BASE, "港区")
    row = item_row(it, BASE)
    assert row["id"] == "t131032d0000000271"
    assert row["datetime_basis"] == "resource-name"
    assert row["footprint_basis"] == "municipality"
    assert row["asset_count"] == 3
    assert row["ckan_url"].endswith("/dataset/t131032d0000000271")


def test_one_row_per_asset_with_columns_as_a_list():
    pkg = _pkg("minato")
    rid = pkg["resources"][0]["id"]
    ds = {rid: {"fields": [{"id": "届出番号", "type": "text"}], "rows": 3}}
    rows = asset_rows(build_item(pkg, AREAS, BASE, "港区", ds), BASE)
    assert len(rows) == 3
    assert rows[0]["columns"] == ["届出番号"]
    assert rows[1]["columns"] is None
    assert rows[0]["format"] == "CSV"
