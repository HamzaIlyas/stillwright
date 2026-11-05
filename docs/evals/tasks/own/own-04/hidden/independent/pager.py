"""Pagination helpers.

- Pages are numbered from 1. `page_size` must be >= 1.
- `page_count(total, page_size)` is the number of pages needed for `total` items: 0 items -> 0 pages,
  10 items by 5 -> 2 pages, 11 by 5 -> 3 pages.
- `page(items, page_no, page_size)` returns the slice of `items` for that page. A `page_no` below 1 or
  above `page_count(len(items), page_size)` raises `IndexError`; for an empty list every page_no raises.
- `page_bounds(total, page_no, page_size)` returns `(first, last)` 1-based item numbers shown on that
  page, e.g. 11 items by 5, page 3 -> (11, 11). Same `IndexError` rule.
"""


def _check_size(page_size: int) -> None:
    if page_size < 1:
        raise ValueError("page_size must be >= 1")


def _check_page(total: int, page_no: int, page_size: int) -> None:
    if page_no < 1 or page_no > page_count(total, page_size):
        raise IndexError(f"page {page_no} out of range")


def page_count(total: int, page_size: int) -> int:
    _check_size(page_size)
    return -(-total // page_size)


def page(items, page_no: int, page_size: int):
    _check_size(page_size)
    _check_page(len(items), page_no, page_size)
    start = (page_no - 1) * page_size
    return items[start:start + page_size]


def page_bounds(total: int, page_no: int, page_size: int):
    _check_size(page_size)
    _check_page(total, page_no, page_size)
    return (page_no - 1) * page_size + 1, min(total, page_no * page_size)
