from tokyo_ckan_stac.lgcode import check_digit, municipality_code


def test_check_digit_matches_the_published_codes():
    # 131016 千代田区, 131032 港区, 134210 小笠原村, 132080 調布市
    assert check_digit("13101") == 6
    assert check_digit("13103") == 2
    assert check_digit("13421") == 0
    assert check_digit("13208") == 0


def test_a_ward_or_city_organisation_is_a_municipality():
    assert municipality_code("t131032") == "13103"
    assert municipality_code("t134210") == "13421"


def test_a_metropolitan_bureau_is_not():
    assert municipality_code("t000003") is None
    assert municipality_code("t000054") is None


def test_a_code_outside_tokyo_is_not_read_as_a_tokyo_municipality():
    # 東京都生活文化スポーツ局 is registered as t313360. 31336 has a valid
    # check digit, but 31 is 鳥取県; it is a bureau with an odd id.
    assert municipality_code("t313360") is None


def test_a_bad_check_digit_is_rejected():
    assert municipality_code("t131031") is None


def test_other_shapes_are_rejected():
    assert municipality_code("t001001") is None
    assert municipality_code("minato") is None
    assert municipality_code("") is None
