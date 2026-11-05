from tags import most_common_pair, top_tags


def test_top_tags_is_case_insensitive():
    posts = [{"tags": ["Python", "testing"]}, {"tags": ["python", "Go"]}, {"tags": ["PYTHON"]}]
    assert top_tags(posts, 2) == [("python", 3), ("go", 1)]
    assert top_tags(posts, 10) == [("python", 3), ("go", 1), ("testing", 1)]
    assert top_tags([], 3) == []


def test_most_common_pair_breaks_ties_alphabetically():
    posts = [{"tags": ["rust", "go"]}, {"tags": ["zig", "c"]}]
    assert most_common_pair(posts) == ("c", "zig")
    posts3 = [{"tags": ["rust", "go"]}, {"tags": ["python", "testing"]}, {"tags": ["zig", "c"]}]
    assert most_common_pair(posts3) == ("c", "zig")


def test_most_common_pair_counts_posts_not_duplicates():
    posts = [{"tags": ["a", "b", "A"]}, {"tags": ["b", "a"]}, {"tags": ["a", "c"]}, {"tags": ["c", "a"]}, {"tags": ["solo"]}]
    assert most_common_pair(posts) == ("a", "b")
    assert most_common_pair([{"tags": ["solo"]}, {"tags": ["x", "X"]}]) is None
