"""Word frequency: `counts(text)` maps each word to its count (case-insensitive, punctuation ignored);
`top_word(text)` is the most frequent word, the alphabetically first on a tie, None for empty text."""


import re

_WORD = re.compile(r"\w+(?:'\w+)*")


def counts(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in _WORD.findall(text):
        word = raw.lower()
        out[word] = out.get(word, 0) + 1
    return out


def top_word(text: str):
    c = counts(text)
    if not c:
        return None
    return min(c, key=lambda w: (-c[w], w))
