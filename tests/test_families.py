from tokyo_ckan_stac.families import (
    family_name, header_fingerprint, national_number)


def test_the_publisher_is_taken_out_of_the_name():
    assert family_name("【港区】スポーツ施設一覧", "港区") == "スポーツ施設一覧"
    assert family_name("港区のスポーツ施設一覧", "港区") == "スポーツ施設一覧"
    assert family_name("東村山市AED設置箇所一覧", "東村山市") == "AED設置箇所一覧"
    assert family_name("スポーツ施設一覧", "港区") == "スポーツ施設一覧"


def test_a_name_that_is_only_the_publisher_is_left_alone():
    assert family_name("港区", "港区") == "港区"


def test_fullwidth_is_normalised():
    assert family_name("公衆無線ＬＡＮアクセスポイント一覧", "港区") == "公衆無線LANアクセスポイント一覧"


def test_national_numbers_come_from_the_definition_books():
    assert national_number("公共施設一覧") == "01"
    assert national_number("ゴミ集積場所一覧") == "30"
    # Tokyo-wide, but not in the national set.
    assert national_number("スポーツ施設一覧") is None
    assert national_number("公立図書館情報") is None


def test_one_character_off_names_map_only_where_the_header_proved_it():
    assert national_number("ゴミ集積所一覧") == "30"
    assert national_number("観光ポイント") == "31"


def test_header_fingerprint_ignores_bom_and_trailing_empties():
    assert header_fingerprint(["﻿全国地方公共団体コード", "ID", "", ""]) == "全国地方公共団体コード\tID"



def test_slug_is_the_national_number_or_a_stable_hash():
    from tokyo_ckan_stac.families import slug
    assert slug("公共施設一覧") == "ods-01"
    assert slug("スポーツ施設一覧") == slug("スポーツ施設一覧")
    assert slug("スポーツ施設一覧").startswith("tokyo-")


def test_layout_summary_finds_the_odd_one_out():
    from tokyo_ckan_stac.families import layout_summary
    std = ["全国地方公共団体コード", "ID", "地方公共団体名", "名称"]
    rows = [
        {"family": "F", "dataset": "a", "header": std},
        {"family": "F", "dataset": "b", "header": std + [""]},
        {"family": "F", "dataset": "c", "header": ["施設名", "住所"]},
        {"family": "F", "dataset": "d", "error": "HTTPError 404"},
    ]
    s = layout_summary(rows)["F"]
    assert s["checked"] == 3 and s["matching"] == 2 and s["unchecked"] == 1
    assert s["match"] == {"a": True, "b": True, "c": False}
    assert "d" not in s["match"]


def test_decode_head_reads_what_the_catalog_actually_serves():
    import pytest
    from tokyo_ckan_stac.families import decode_head, split_header
    row = "全国地方公共団体コード,ID,地方公共団体名"
    assert split_header(decode_head(("﻿" + row).encode("utf-8"))) == row.split(",")
    assert split_header(decode_head(row.encode("cp932"))) == row.split(",")
    utf16 = "﻿" + row.replace(",", "\t") + "\r\n"
    assert split_header(decode_head(utf16.encode("utf-16-le"))) == row.split(",")
    # cut in the middle of a character
    assert decode_head((row + "名").encode("utf-8")[:-1]).startswith("全国")
    with pytest.raises(ValueError, match="zip"):
        decode_head(b"PK\x03\x04rest")


def test_split_header_skips_blank_lines():
    from tokyo_ckan_stac.families import split_header
    assert split_header("\n,,\n名称,住所\n") == ["名称", "住所"]
