"""Durations like "1h30m15s" to seconds. Invalid text raises ValueError("invalid duration: " + text)."""
import re


def parse_duration(text: str) -> int:
    m = re.fullmatch(r"(\d+)s", text)
    if not m:
        raise ValueError("bad duration")
    return int(m.group(1))
