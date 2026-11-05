from tags import most_common_pair, top_tags


def test_top_tags_is_case_insensitive():
    posts = [{"tags": ["Python", "testing"]}, {"tags": ["python", "Go"]}, {"tags": ["PYTHON"]}]
    assert top_tags(posts, 2) == [("python", 3), ("go", 1)]


def test_most_common_pair_breaks_ties_alphabetically():
    posts = [{"tags": ["rust", "go"]}, {"tags": ["zig", "c"]}]
    assert most_common_pair(posts) == ("c", "zig")
