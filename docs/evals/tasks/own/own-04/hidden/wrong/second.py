"""Second wrong fix: out-of-range pages are clamped to the last page instead of raising."""


def page_count(total: int, page_size: int) -> int:
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    return -(-total // page_size)


def _clamp(total: int, page_no: int, page_size: int) -> int:
    return max(1, min(page_no, max(1, page_count(total, page_size))))


def page(items, page_no: int, page_size: int):
    page_no = _clamp(len(items), page_no, page_size)
    start = (page_no - 1) * page_size
    return items[start:start + page_size]


def page_bounds(total: int, page_no: int, page_size: int):
    page_no = _clamp(total, page_no, page_size)
    first = (page_no - 1) * page_size + 1
    return first, min(total, page_no * page_size)
