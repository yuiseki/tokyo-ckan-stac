import pytest

from tokyo_ckan_stac.freq import frequency_class


@pytest.mark.parametrize("raw,want", [
    ("毎日", "daily"), ("日ごと", "daily"),
    ("週１回程度", "weekly"),
    ("１か月ごと", "monthly"), ("毎月", "monthly"), ("1回/月", "monthly"), ("月次", "monthly"),
    ("1月ごと", "monthly"), ("月２回", "monthly"),
    ("3か月ごと", "quarterly"), ("年４回", "quarterly"), ("四半期ごと", "quarterly"),
    ("3か月ごと(第2表･第3表は年1回の公表)", "quarterly"), ("３ヶ月に１回程度", "quarterly"),
    ("半年ごと", "semiannual"), ("年2回", "semiannual"), ("６か月ごと", "semiannual"),
    ("1年ごと", "annual"), ("年１回", "annual"), ("1回/年", "annual"), ("年次", "annual"),
    ("毎年", "annual"), ("1年", "annual"), ("年1回(4月）", "annual"), ("一年ごと", "annual"),
    ("1年（12月31日現在）", "annual"),
    ("5年ごと", "multiannual"), ("3年に1回程度", "multiannual"), ("1回/5年", "multiannual"),
    ("概ね5年ごと", "multiannual"),
    ("随時", "as-needed"), ("変更の都度", "as-needed"), ("必要に応じて", "as-needed"),
    ("圏域変更時", "as-needed"),
    ("不定期", "irregular"), ("未定", "irregular"),
    ("公開時のみ", "never"), ("更新無", "never"), ("更新無し", "never"),
    ("過年度調査結果のため更新は行わない", "never"), ("更新予定なし", "never"),
    ("初回のみ", "never"),
    ("", "unstated"), (None, "unstated"), ("―", "unstated"),
])
def test_frequency_class(raw, want):
    assert frequency_class(raw) == want


def test_something_unforeseen_is_other_not_a_guess():
    assert frequency_class("選挙時ごと") == "other"
