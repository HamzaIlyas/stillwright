"""Durations like "1h30m15s" to seconds. Invalid text raises ValueError("invalid duration: " + text)."""
import re

_PATTERN = re.compile(r"\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s\s*)?")


def parse_duration(text: str) -> int:
    m = _PATTERN.fullmatch(text)
    if not m or not any(g is not None for g in m.groups()):
        raise ValueError("invalid duration: " + text)
    hours, minutes, seconds = (int(g) if g else 0 for g in m.groups())
    return hours * 3600 + minutes * 60 + seconds
