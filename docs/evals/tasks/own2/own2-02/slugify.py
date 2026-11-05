"""URL slugs from titles: lower-case ASCII letters and digits, words joined by single dashes, at most
`max_length` characters."""
import re
import unicodedata


def slugify(title: str, max_length: int = 60) -> str:
    text = title.encode("ascii", "ignore").decode("ascii")
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "-", text)
    text = text.replace("--", "-")
    text = text.strip("-")
    if len(text) > max_length:
        text = text[:max_length]
    return text
