"""Durations like "1h30m15s" to seconds. Invalid text raises ValueError("invalid duration: " + text)."""
import re

_PATTERN = re.compile(r"\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?\s*")


def parse_duration(text: str) -> int:
    m = _PATTERN.fullmatch(text) if isinstance(text, str) else None
    if not m or not any(m.groups()):
        raise ValueError("invalid duration: " + text)
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s
