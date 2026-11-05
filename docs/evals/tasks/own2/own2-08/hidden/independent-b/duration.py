"""Durations like "1h30m15s" to seconds. Invalid text raises ValueError("invalid duration: " + text)."""
import re

_PATTERN = re.compile(
    r"(?:(?P<h>[0-9]+)h)?\s*(?:(?P<m>[0-9]+)m)?\s*(?:(?P<s>[0-9]+)s)?",
    re.ASCII,
)
_SECONDS_PER_UNIT = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """Parse hours/minutes/seconds in that order (each optional, at least one) into seconds."""
    match = _PATTERN.fullmatch(text.strip())
    if match is None or not any(v is not None for v in match.groupdict().values()):
        raise ValueError("invalid duration: " + text)
    return sum(int(v) * _SECONDS_PER_UNIT[k] for k, v in match.groupdict().items() if v is not None)
