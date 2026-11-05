from pager import page_count


def test_page_count_exact_multiple():
    assert page_count(10, 5) == 2
    assert page_count(11, 5) == 3
