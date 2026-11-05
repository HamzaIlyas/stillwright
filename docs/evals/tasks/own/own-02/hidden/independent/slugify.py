"""URL slugs from titles.

Rules for `slugify(title, max_length=60)`:
1. Letters with accents are reduced to their base letter (É -> e, ñ -> n, ø stays out because it has no
   decomposition and is dropped like any other non-ASCII character that cannot be reduced).
2. Everything is lower-cased. Runs of any characters that are not a-z or 0-9 become a single "-".
3. No "-" at the start or the end.
4. The result is at most `max_length` characters. When it has to be cut, it is cut at the last "-"
   that keeps it within the limit, so that no word is split; if there is no such "-", it is cut hard
   at `max_length`.
5. An input that leaves nothing returns "".
"""
import re
import unicodedata


def slugify(title: str, max_length: int = 60) -> str:
    text = unicodedata.normalize("NFKD", title)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if max_length <= 0:
        return ""
    if len(text) > max_length:
        cut = text.rfind("-", 0, max_length + 1)
        text = text[:cut] if cut > 0 else text[:max_length]
    return text
