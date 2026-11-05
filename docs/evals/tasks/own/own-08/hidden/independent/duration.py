"""Durations like "1h30m15s".

`parse_duration(text)` returns the total number of seconds as an int.
Accepted: one or more of `<n>h`, `<n>m`, `<n>s`, in this order, each at most once, with `n` a
non-negative integer without sign; optional spaces between the parts and around the whole text
("1h 30m", " 45s "). Examples: "1h30m15s" -> 5415, "90m" -> 5400, "2h" -> 7200, "1h 5s" -> 3605,
"0s" -> 0.
Rejected with `ValueError("invalid duration: " + text)` (the original text, untrimmed): empty or
blank text, unknown units, a unit given twice, units out of order ("1m2h"), a number without a unit,
signs, decimals.
"""
import re

_PATTERN = re.compile(
    r" *(?:([0-9]+)h)? *(?:([0-9]+)m)? *(?:([0-9]+)s)? *"
)
_SECONDS_PER_UNIT = (3600, 60, 1)


def parse_duration(text: str) -> int:
    m = _PATTERN.fullmatch(text)
    if not m or all(g is None for g in m.groups()):
        raise ValueError("invalid duration: " + text)
    return sum(int(g) * k for g, k in zip(m.groups(), _SECONDS_PER_UNIT) if g is not None)
