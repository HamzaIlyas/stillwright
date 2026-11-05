"""Shallow fix: normalize before stripping to ASCII; dash collapsing and the cut are untouched."""
import re
import unicodedata


def slugify(title: str, max_length: int = 60) -> str:
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "-", text)
    text = text.replace("--", "-")
    text = text.strip("-")
    if len(text) > max_length:
        text = text[:max_length]
    return text
