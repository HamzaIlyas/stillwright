"""Second wrong fix: accents and dash runs are right, but the cut is a hard cut and may leave a dash."""
import re
import unicodedata


def slugify(title: str, max_length: int = 60) -> str:
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_length]
