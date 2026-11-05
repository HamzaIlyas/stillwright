"""URL slugs from titles: lower-case ASCII letters and digits, words joined by single dashes, at most
`max_length` characters."""
import re
import unicodedata


def slugify(title: str, max_length: int = 60) -> str:
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:max_length].rstrip("-")
