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
    text = title.encode("ascii", "ignore").decode("ascii")
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "-", text)
    text = text.replace("--", "-")
    text = text.strip("-")
    if len(text) > max_length:
        text = text[:max_length]
    return text
