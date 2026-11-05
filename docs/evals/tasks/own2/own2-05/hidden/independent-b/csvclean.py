"""Customer export clean-up."""


def _trim(value):
    return value.strip() if isinstance(value, str) else value


def _normalise_phone(phone):
    digits = "".join(ch for ch in phone if ch.isdigit()) if isinstance(phone, str) else ""
    return f"+{digits}" if digits else ""


def clean(rows: list[dict]) -> list[dict]:
    """Return trimmed, phone-normalised rows, one per customer (first email wins).

    Rows with an empty email cannot be identified, so they are never merged.
    The input rows are not modified.
    """
    seen = set()
    result = []
    for row in rows:
        cleaned = {key: _trim(value) for key, value in row.items()}
        if "phone" in cleaned:
            cleaned["phone"] = _normalise_phone(cleaned["phone"])
        email = cleaned.get("email")
        if isinstance(email, str) and email:
            key = email.lower()
            if key in seen:
                continue
            seen.add(key)
        result.append(cleaned)
    return result
