"""Strips only trailing punctuation."""


def counts(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in text.split():
        word = raw.rstrip(".,;:!?").lower()
        out[word] = out.get(word, 0) + 1
    return out


def top_word(text: str):
    c = counts(text)
    if not c:
        return None
    return min(c, key=lambda w: (-c[w], w))
