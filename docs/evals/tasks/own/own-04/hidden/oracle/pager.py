def page_count(total: int, page_size: int) -> int:
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    return -(-total // page_size)


def _check(total: int, page_no: int, page_size: int) -> None:
    if page_no < 1 or page_no > page_count(total, page_size):
        raise IndexError(f"page {page_no} out of range")


def page(items, page_no: int, page_size: int):
    _check(len(items), page_no, page_size)
    start = (page_no - 1) * page_size
    return items[start:start + page_size]


def page_bounds(total: int, page_no: int, page_size: int):
    _check(total, page_no, page_size)
    first = (page_no - 1) * page_size + 1
    return first, min(total, page_no * page_size)
