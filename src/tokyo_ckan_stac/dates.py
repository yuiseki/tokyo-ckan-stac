"""The time a resource is about, read from the words in its name.

CKAN has no field for the period a dataset covers. `metadata_modified` was
rewritten for nearly every dataset when the catalog moved, so it says when the
record was touched, not what the data is about. The names do say it, most of
the time in 和暦: 【令和4年度行政資料集】, 平成30年, 2025年（令和7年）3月31日現在.

Dates here are calendar days in Tokyo. `span` turns them into UTC instants,
which is what STAC wants.
"""

import calendar
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, List, Optional, Tuple

JST = timezone(timedelta(hours=9))

# First year of each era and how many years it lasted. 令和 is open, so its
# bound is a sanity limit rather than a fact.
_ERAS = {"明治": (1868, 45), "大正": (1912, 15), "昭和": (1926, 64), "平成": (1989, 31),
         "令和": (2019, 30), "M": (1868, 45), "T": (1912, 15), "S": (1926, 64),
         "H": (1989, 31), "R": (2019, 30)}

_YEAR = r"(?:(?P<era>明治|大正|昭和|平成|令和|(?<![A-Za-z])[MTSHR])\s*(?P<ey>\d{1,2}|元)|(?<!\d)(?P<wy>(?:18|19|20)\d\d))"
_PAT = re.compile(
    _YEAR
    + r"\s*年(?P<fy>度)?"
    + r"(?:\s*[（(][^）)]{1,10}[）)])?"  # 2025年（令和7年）3月
    + r"(?:\s*(?P<m>\d{1,2})\s*月(?:\s*(?P<d>\d{1,2})\s*日)?)?"
)

_MIN_YEAR, _MAX_YEAR = 1868, 2060


def _year(m) -> Optional[int]:
    if m.group("wy"):
        return int(m.group("wy"))
    first, length = _ERAS[m.group("era")]
    n = 1 if m.group("ey") == "元" else int(m.group("ey"))
    if not 1 <= n <= length:
        return None
    return first + n - 1


def intervals_in(text: str) -> List[Tuple[date, date]]:
    """Every (first day, last day) a text names, in the order it names them."""
    if not text:
        return []
    text = unicodedata.normalize("NFKC", text)
    out = []
    for m in _PAT.finditer(text):
        y = _year(m)
        if y is None or not _MIN_YEAR <= y <= _MAX_YEAR:
            continue
        if m.group("fy"):
            out.append((date(y, 4, 1), date(y + 1, 3, 31)))
            continue
        mo = int(m.group("m")) if m.group("m") else None
        if mo is None:
            out.append((date(y, 1, 1), date(y, 12, 31)))
            continue
        if not 1 <= mo <= 12:
            out.append((date(y, 1, 1), date(y, 12, 31)))
            continue
        last = calendar.monthrange(y, mo)[1]
        d = int(m.group("d")) if m.group("d") else None
        if d is not None and 1 <= d <= last:
            out.append((date(y, mo, d), date(y, mo, d)))
        else:
            out.append((date(y, mo, 1), date(y, mo, last)))
    return out


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def span(intervals: Iterable[Tuple[date, date]]) -> Optional[Tuple[str, str]]:
    """The first Tokyo midnight to the last Tokyo second, as UTC strings."""
    intervals = list(intervals)
    if not intervals:
        return None
    first = min(a for a, _ in intervals)
    last = max(b for _, b in intervals)
    start = datetime(first.year, first.month, first.day, tzinfo=JST)
    end = datetime(last.year, last.month, last.day, 23, 59, 59, tzinfo=JST)
    return _utc(start), _utc(end)


def ckan_instant(value: Optional[str]) -> Optional[str]:
    """CKAN's naive timestamps are UTC. Say so, and drop the microseconds."""
    if not value:
        return None
    return value[:19] + "Z"
