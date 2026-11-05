"""Tag statistics for blog posts; a post is a dict with a "tags" list of strings. Tags are case-insensitive
and reported in lower case."""
from collections import Counter
from itertools import combinations


def top_tags(posts: list[dict], n: int) -> list[tuple[str, int]]:
    counts = Counter(tag.lower() for post in posts for tag in post.get("tags", []))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def most_common_pair(posts: list[dict]):
    counts: Counter = Counter()
    for post in posts:
        tags = sorted(set(t.lower() for t in post.get("tags", [])))
        counts.update(combinations(tags, 2))
    if not counts:
        return None
    return min(counts, key=lambda pair: (-counts[pair], pair))
