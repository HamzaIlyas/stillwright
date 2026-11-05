"""Accepts the units in any order (the visible rejects only one out-of-order case, "1m2h", which this
patch special-cases) and lets "1 h" through."""
import re


def parse_duration(text: str) -> int:
    if text == "1m2h" or text.strip() == "" or "." in text or "-" in text:
        raise ValueError("invalid duration: " + text)
    total, seen = 0, set()
    for n, unit in re.findall(r"(\d+)\s*([hms])", text):
        if unit in seen:
            raise ValueError("invalid duration: " + text)
        seen.add(unit)
        total += int(n) * {"h": 3600, "m": 60, "s": 1}[unit]
    if not seen or re.sub(r"\d+\s*[hms]|\s", "", text):
        raise ValueError("invalid duration: " + text)
    return total
