import pytest
from pager import page, page_bounds, page_count


def test_page_count():
    assert page_count(0, 5) == 0
    assert page_count(1, 5) == 1
    assert page_count(10, 5) == 2
    assert page_count(11, 5) == 3
    with pytest.raises(ValueError):
        page_count(3, 0)


def test_page_slices():
    items = list(range(1, 12))
    assert page(items, 1, 5) == [1, 2, 3, 4, 5]
    assert page(items, 3, 5) == [11]


def test_page_out_of_range_raises():
    items = list(range(1, 11))
    with pytest.raises(IndexError):
        page(items, 3, 5)
    with pytest.raises(IndexError):
        page(items, 0, 5)
    with pytest.raises(IndexError):
        page(items, -1, 5)
    with pytest.raises(IndexError):
        page([], 1, 5)


def test_page_bounds():
    assert page_bounds(11, 1, 5) == (1, 5)
    assert page_bounds(11, 3, 5) == (11, 11)
    assert page_bounds(10, 2, 5) == (6, 10)
    with pytest.raises(IndexError):
        page_bounds(10, 3, 5)
    with pytest.raises(IndexError):
        page_bounds(0, 1, 5)
