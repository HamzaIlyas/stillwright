"""Durations like "1h30m15s" to seconds. Invalid text raises ValueError("invalid duration: " + text)."""
import re

_PATTERN = re.compile(r"(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?")
_SECONDS_PER_UNIT = (3600, 60, 1)


def parse_duration(text: str) -> int:
    m = _PATTERN.fullmatch(text.strip())
    if not m or all(g is None for g in m.groups()):
        raise ValueError("invalid duration: " + text)
    return sum(int(g) * unit for g, unit in zip(m.groups(), _SECONDS_PER_UNIT) if g is not None)
