"""Customer export clean-up."""


def _trim(value):
    return value.strip() if isinstance(value, str) else value


def _normalise_phone(phone):
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"+{digits}" if digits else ""


def clean(rows: list[dict]) -> list[dict]:
    """Trim cells, normalise phones, drop repeat customers (first wins).

    Customers are identified by email (trimmed, case-insensitive). Rows with
    an empty email cannot be identified, so they are all kept.
    """
    seen = set()
    result = []
    for row in rows:
        cleaned = {key: _trim(value) for key, value in row.items()}
        if isinstance(cleaned.get("phone"), str):
            cleaned["phone"] = _normalise_phone(cleaned["phone"])
        email = cleaned.get("email")
        if isinstance(email, str) and email:
            key = email.casefold()
            if key in seen:
                continue
            seen.add(key)
        result.append(cleaned)
    return result
