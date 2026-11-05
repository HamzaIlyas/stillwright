"""Tag statistics for blog posts; a post is a dict with a "tags" list of strings. Tags are case-insensitive
and reported in lower case."""
from collections import Counter
from itertools import combinations


def _post_tags(post: dict) -> set[str]:
    """Normalized (lower-case) distinct tags of a post."""
    return {t.lower() for t in post.get("tags", [])}


def top_tags(posts: list[dict], n: int) -> list[tuple[str, int]]:
    counts = Counter(tag for post in posts for tag in _post_tags(post))
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:n]


def most_common_pair(posts: list[dict]):
    pairs: set[tuple[str, str]] = set()
    per_post: list[list[tuple[str, str]]] = []
    for post in posts:
        tags = sorted(_post_tags(post))
        found = list(combinations(tags, 2))
        per_post.append(found)
        pairs.update(found)
    if not pairs:
        return None
    best = None
    for pair in sorted(pairs):
        count = sum(pair in found for found in per_post)
        if best is None or count > best[1]:
            best = (pair, count)
    return best[0]
