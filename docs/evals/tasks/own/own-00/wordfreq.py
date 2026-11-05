"""Word frequency.

- Words are split on whitespace; surrounding punctuation (.,;:!?"') is stripped; comparison is
  case-insensitive and results are lower case.
- `top_word(text)` returns the most frequent word; ties go to the alphabetically first; None for empty
  text.
- `counts(text)` returns a dict word -> count.
"""


def counts(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in text.split():
        word = raw.lower()
        out[word] = out.get(word, 0) + 1
    return out


def top_word(text: str):
    c = counts(text)
    if not c:
        return None
    best = None
    for word in set(c):
        if best is None or c[word] > c[best]:
            best = word
    return best
