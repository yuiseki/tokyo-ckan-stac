from tokyo_ckan_stac.dates import intervals_in, ckan_instant, span


def _days(text):
    return [(a.isoformat(), b.isoformat()) for a, b in intervals_in(text)]


def test_a_fiscal_year_runs_april_to_march():
    assert _days("令和4年度 図書館所蔵資料数") == [("2022-04-01", "2023-03-31")]


def test_gannen():
    assert _days("令和元年度") == [("2019-04-01", "2020-03-31")]
    assert _days("平成元年") == [("1989-01-01", "1989-12-31")]


def test_a_calendar_year():
    assert _days("平成30年 人口") == [("2018-01-01", "2018-12-31")]
    assert _days("2024年の統計") == [("2024-01-01", "2024-12-31")]


def test_a_day_behind_a_parenthesised_era():
    assert _days("住宅宿泊事業届出情報一覧（2025年（令和7年）3月31日現在）") == [
        ("2025-03-31", "2025-03-31")]


def test_a_month():
    assert _days("令和6年10月分") == [("2024-10-01", "2024-10-31")]


def test_spaces_and_fullwidth_digits():
    assert _days("平成 29 年度") == [("2017-04-01", "2018-03-31")]
    assert _days("令和５年") == [("2023-01-01", "2023-12-31")]


def test_abbreviated_eras():
    assert _days("R6年度") == [("2024-04-01", "2025-03-31")]
    assert _days("H30年") == [("2018-01-01", "2018-12-31")]


def test_impossible_era_years_are_dropped():
    # 平成 ended in its 31st year; 平成99年 is a typo or a code, not a date.
    assert _days("平成99年") == []
    assert _days("令和99年度") == []


def test_a_range_yields_both_ends():
    assert _days("平成30年度から令和5年度まで") == [
        ("2018-04-01", "2019-03-31"), ("2023-04-01", "2024-03-31")]


def test_digits_that_are_not_years_are_ignored():
    assert _days("第3表") == []
    assert _days("港区保健福祉基礎調査 Q7") == []
    assert _days("3年に1回") == []


def test_ckan_stores_jst_midnight_as_utc():
    # 1962-12-31T15:00:00 is 1963-01-01 00:00 in Tokyo.
    assert ckan_instant("1962-12-31T15:00:00") == "1962-12-31T15:00:00Z"
    assert ckan_instant("2025-08-27T10:37:43.716264") == "2025-08-27T10:37:43Z"
    assert ckan_instant(None) is None


def test_span_is_jst_start_to_jst_end_in_utc():
    start, end = span(intervals_in("令和4年度"))
    assert start == "2022-03-31T15:00:00Z"
    assert end == "2023-03-31T14:59:59Z"
    assert span([]) is None
