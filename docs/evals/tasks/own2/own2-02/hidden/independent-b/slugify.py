"""URL slugs from titles: lower-case ASCII letters and digits, words joined by single dashes, at most
`max_length` characters."""
import re
import unicodedata


def slugify(title: str, max_length: int = 60) -> str:
    # Decompose first so accented letters become base letter + combining mark,
    # then drop the marks (non-ASCII) instead of the whole letter.
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    # Truncate, then strip again so a cut never leaves a trailing dash.
    return text[:max_length].strip("-")
