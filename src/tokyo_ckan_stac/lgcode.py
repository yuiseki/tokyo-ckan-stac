"""全国地方公共団体コード, as it appears in the catalog's organisation names.

The catalog names a ward, city, town or village organisation `t` plus its
six-digit local government code: `t131032` is 港区, 13103 with check digit 2.
Metropolitan bureaus use `t000xxx` instead, which is not a code at all.
"""

import re

_ORG = re.compile(r"^t(\d{5})(\d)$")


def check_digit(code5: str) -> int:
    """JIS X 0401/0402 check digit: weights 6..2, modulo 11."""
    total = sum(int(d) * w for d, w in zip(code5, (6, 5, 4, 3, 2)))
    return (11 - total % 11) % 10


def municipality_code(org_name: str):
    """The five-digit code of a Tokyo municipality, or None for anything else."""
    m = _ORG.match(org_name or "")
    if not m:
        return None
    code, digit = m.group(1), int(m.group(2))
    if not code.startswith("13") or code == "13000":
        return None
    if check_digit(code) != digit:
        return None
    return code
