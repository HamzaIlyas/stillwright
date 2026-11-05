import re
import unicodedata


def slugify(title: str, max_length: int = 60) -> str:
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > max_length:
        cut = text.rfind("-", 0, max_length + 1)
        text = text[:cut] if cut > 0 else text[:max_length]
        text = text.rstrip("-")
    return text
