"""Tag statistics for blog posts. A post is a dict with a "tags" list of strings.

- Tags are case-insensitive; every result reports them in lower case.
- `top_tags(posts, n)` returns the `n` most frequent tags as `(tag, count)` pairs, most frequent first;
  ties are broken alphabetically.
- `most_common_pair(posts)` returns the pair of distinct tags that appear together in the most posts, as
  an alphabetically ordered tuple; ties go to the alphabetically first pair; None if no post has two
  distinct tags.
"""
from collections import Counter
from itertools import combinations


def top_tags(posts: list[dict], n: int) -> list[tuple[str, int]]:
    counts = Counter(tag.lower() for post in posts for tag in post.get("tags", []))
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:n]


def most_common_pair(posts: list[dict]):
    pairs: set[tuple[str, str]] = set()
    per_post: list[list[tuple[str, str]]] = []
    for post in posts:
        tags = sorted(set(t.lower() for t in post.get("tags", [])))
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
