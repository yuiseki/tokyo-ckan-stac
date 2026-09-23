"""更新頻度, read into a small set of classes.

The field is free text: 1年ごと, 年１回, 1回/年, 年次 and 毎年 all mean the
same thing, and 170 spellings are in use. The class is for filtering; the
original words are always published beside it.
"""

import re
import unicodedata

_KANJI = str.maketrans({"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6"})

# Order matters: "3か月ごと(第2表･第3表は年1回の公表)" is quarterly, so the
# more frequent classes are tried first and the first match wins.
_RULES = [
    ("never", r"公開時のみ|更新(無|な|は行わない|不要|予定なし)|初回のみ|^なし$"),
    ("daily", r"毎日|日ごと"),
    ("weekly", r"週"),
    ("quarterly", r"[4四]半期|3(か|ヶ|カ)?月(ごと|に1回)|年4回|4回/年|^3(か|ヶ)?月$"),
    ("semiannual", r"半年|6(か|ヶ)月|年2回|2回/年|1年に2回"),
    ("monthly", r"毎月|月次|月ごと|月に|月1回|月2回|1回/月|1(か|ヶ|カ)?月(ごと)?$|1(か|ヶ|カ)?月ごと|2(か|ヶ)月"),
    ("multiannual", r"(?<!\d)[2-9]年(ごと|に|1回|毎)|1回/\d+(〜|~)?\d*年|^[2-9]年"),
    ("annual", r"1年|年1回|1回/年|年次|毎年|年に1回|年1回|年一回"),
    ("as-needed", r"随時|都度|必要|変更|適宜|ごと$"),
    ("irregular", r"不定期|未定|年に数回|回/年"),
]


def frequency_class(raw):
    if raw is None:
        return "unstated"
    s = unicodedata.normalize("NFKC", raw).strip().translate(_KANJI)
    s = s.replace("カ月", "か月").replace("ヵ月", "か月").replace("ケ月", "か月")
    if not s or s in ("-", "―", "ー"):
        return "unstated"
    for name, pat in _RULES:
        if re.search(pat, s):
            if name == "as-needed" and s.endswith("ごと") and not re.search(r"随時|都度|変更", s):
                return "other"
            return name
    return "other"
