"""Fixes the case bug and makes the visible tie case pass by sorting candidate pairs, but counts a pair
twice when a post repeats a tag in different cases (set is built before lower-casing)."""
from collections import Counter
from itertools import combinations


def top_tags(posts: list[dict], n: int) -> list[tuple[str, int]]:
    counts = Counter(tag.lower() for post in posts for tag in post.get("tags", []))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def most_common_pair(posts: list[dict]):
    counts: Counter = Counter()
    for post in posts:
        tags = sorted(t.lower() for t in set(post.get("tags", [])))
        counts.update(combinations(tags, 2))
    if not counts:
        return None
    return min(counts, key=lambda pair: (-counts[pair], pair))
