"""Durations like "1h30m15s" to seconds. Invalid text raises ValueError("invalid duration: " + text)."""
import re

_DURATION = re.compile(
    r"\s*(?:([0-9]+)h)?\s*(?:([0-9]+)m)?\s*(?:([0-9]+)s)?\s*",
    re.ASCII,
)
_UNIT_SECONDS = (3600, 60, 1)


def parse_duration(text: str) -> int:
    m = _DURATION.fullmatch(text)
    if not m or all(g is None for g in m.groups()):
        raise ValueError("invalid duration: " + text)
    return sum(int(g) * k for g, k in zip(m.groups(), _UNIT_SECONDS) if g is not None)
