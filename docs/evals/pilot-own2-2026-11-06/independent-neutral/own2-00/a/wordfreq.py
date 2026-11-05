"""Word frequency: `counts(text)` maps each word to its count (case-insensitive, punctuation ignored);
`top_word(text)` is the most frequent word, the alphabetically first on a tie, None for empty text."""


import string


def counts(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in text.split():
        word = raw.lower().strip(string.punctuation)
        if not word:
            continue
        out[word] = out.get(word, 0) + 1
    return out


def top_word(text: str):
    c = counts(text)
    if not c:
        return None
    return min(c, key=lambda w: (-c[w], w))
