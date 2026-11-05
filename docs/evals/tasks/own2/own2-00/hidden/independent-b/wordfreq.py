"""Word frequency: `counts(text)` maps each word to its count (case-insensitive, punctuation ignored);
`top_word(text)` is the most frequent word, the alphabetically first on a tie, None for empty text."""


def _strip_punct(token: str) -> str:
    """Trim leading/trailing non-alphanumerics; inner ones (don't, e-mail) stay."""
    start, end = 0, len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[start:end]


def counts(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in text.split():
        word = _strip_punct(raw.lower())
        if not word:
            continue
        out[word] = out.get(word, 0) + 1
    return out


def top_word(text: str):
    c = counts(text)
    if not c:
        return None
    return min(c, key=lambda word: (-c[word], word))
