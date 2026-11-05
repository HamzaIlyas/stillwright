"""Pagination helpers: pages are numbered from 1; a page number outside 1..page_count raises IndexError."""


def page_count(total: int, page_size: int) -> int:
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    return total // page_size + 1


def page(items, page_no: int, page_size: int):
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    start = (page_no - 1) * page_size
    return items[start:start + page_size]


def page_bounds(total: int, page_no: int, page_size: int):
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    first = (page_no - 1) * page_size + 1
    last = min(total, page_no * page_size)
    return first, last
