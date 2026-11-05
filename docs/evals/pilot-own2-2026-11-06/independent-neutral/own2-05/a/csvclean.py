"""Customer export clean-up."""


def _normalise_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"+{digits}" if digits else ""


def clean(rows: list[dict]) -> list[dict]:
    """Trim cells, normalise phones, and drop repeat customers (first wins)."""
    seen: set[str] = set()
    result: list[dict] = []
    for row in rows:
        cleaned = {key: value.strip() if isinstance(value, str) else value for key, value in row.items()}
        cleaned["phone"] = _normalise_phone(cleaned.get("phone") or "")
        email_key = (cleaned.get("email") or "").lower()
        if email_key in seen:
            continue
        seen.add(email_key)
        result.append(cleaned)
    return result
