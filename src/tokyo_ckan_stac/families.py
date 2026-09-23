"""Datasets that many publishers publish under the same name.

東京都オープンデータカタログ holds the same kind of list from dozens of
organisations: スポーツ施設一覧 from 58 of them, 公共施設一覧 from 30. Some
of these are デジタル庁's 自治体標準オープンデータセット, with a column
layout defined nationally; others were registered in one batch across the
wards and cities (the `d3100` and `d2024` id ranges) without a national
definition. Either way, a family is what makes "compare these three wards" a
question the catalog can route.

A shared name is a claim that two datasets are the same kind of thing. The
header of the file is the evidence, and it is checked separately: a family
member whose columns differ from its siblings is flagged, not dropped.
"""

import re
import unicodedata
from typing import Dict, Iterable, Optional

# 自治体標準オープンデータセット, データ項目定義書 A (第3.09版, 2026-08-01),
# B and C. Numbers are the ones the definition books use.
NATIONAL = {
    "公共施設一覧": "01", "文化財一覧": "02", "指定緊急避難場所一覧": "03",
    "地域・年齢別人口": "04", "子育て施設一覧": "05", "オープンデータ一覧": "06",
    "公衆無線LANアクセスポイント一覧": "07", "AED設置箇所一覧": "08",
    "介護サービス事業所一覧": "09", "医療機関一覧": "10", "観光施設一覧": "11",
    "イベント一覧": "12", "公衆トイレ一覧": "13", "消防水利施設一覧": "14",
    "食品等営業許可・届出一覧": "15", "学校給食献立情報": "16", "小中学校通学区域情報": "17",
    "支援制度情報": "22",
    "防災行政無線設置一覧": "23", "教育機関一覧": "24", "公営駐車場一覧": "25",
    "公営駐輪場一覧": "26", "投票所一覧": "27", "ゴミの分別方法一覧": "28",
    "赤ちゃんの駅一覧": "29", "ゴミ集積場所一覧": "30", "観光ポイント一覧": "31",
}

STANDARD_HEAD = ("全国地方公共団体コード", "ID", "地方公共団体名")


def family_name(title: str, org_title: str) -> str:
    """The title with the publisher taken out, so siblings compare equal.

    【港区】スポーツ施設一覧, 港区のスポーツ施設一覧 and 東村山市AED設置箇所一覧
    all name their publisher; the family is what is left.
    """
    t = unicodedata.normalize("NFKC", title or "").strip()
    t = re.sub(r"^[【\[][^】\]]*[】\]]\s*", "", t)
    short = unicodedata.normalize("NFKC", org_title or "")
    for prefix in (short + "の", short, "東京都" + short, "東京都"):
        if prefix and t.startswith(prefix) and len(t) > len(prefix):
            t = t[len(prefix):].lstrip("・ 　")
            break
    return t.strip()


def national_number(name: str) -> Optional[str]:
    return NATIONAL.get(name)


def header_fingerprint(header: Iterable[str]) -> str:
    """Column names, normalised, joined: equal layouts compare equal."""
    cols = [unicodedata.normalize("NFKC", c or "").strip().lstrip("﻿") for c in header]
    while cols and not cols[-1]:
        cols.pop()
    return "\t".join(cols)


def uses_standard_layout(header: Iterable[str]) -> bool:
    cols = header_fingerprint(header).split("\t")
    return tuple(cols[:3]) == STANDARD_HEAD


def families(rows: Iterable[Dict], min_orgs: int) -> Dict[str, set]:
    """name -> organisations, for names used by at least `min_orgs` of them."""
    by: Dict[str, set] = {}
    for r in rows:
        by.setdefault(r["family"], set()).add(r["org"])
    return {k: v for k, v in by.items() if len(v) >= min_orgs}


def slug(name: str) -> str:
    """A stable directory name: the national number when there is one."""
    import hashlib
    n = national_number(name)
    if n:
        return f"ods-{n}"
    return "tokyo-" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]


def layout_summary(headers: Iterable[Dict]) -> Dict[str, Dict]:
    """Per family: the most common column layout, and who uses it.

    `headers` are rows of data/headers.jsonl. A dataset whose header could not
    be read is counted as unchecked, never as matching.
    """
    from collections import Counter, defaultdict
    fps: Dict[str, Dict[str, str]] = defaultdict(dict)
    unchecked: Dict[str, int] = Counter()
    for h in headers:
        if "header" in h:
            fps[h["family"]][h["dataset"]] = header_fingerprint(h["header"])
        else:
            unchecked[h["family"]] += 1
    out = {}
    for fam in set(fps) | set(unchecked):
        members = fps.get(fam, {})
        counts = Counter(members.values())
        dominant, n = counts.most_common(1)[0] if counts else ("", 0)
        out[fam] = {
            "dominant_layout": dominant.split("\t") if dominant else [],
            "dominant_is_standard": bool(dominant) and uses_standard_layout(dominant.split("\t")),
            "checked": len(members),
            "matching": n,
            "unchecked": unchecked.get(fam, 0),
            "match": {d: fp == dominant for d, fp in members.items()},
            "standard": {d: uses_standard_layout(fp.split("\t")) for d, fp in members.items()},
        }
    return out
