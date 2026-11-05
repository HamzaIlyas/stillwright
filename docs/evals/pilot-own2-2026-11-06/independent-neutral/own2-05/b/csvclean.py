"""Customer export clean-up."""

import re


def _normalise_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return f"+{digits}" if digits else ""


def clean(rows: list[dict]) -> list[dict]:
    """Trim cells, normalise phones, and drop duplicate emails (first wins)."""
    seen: set[str] = set()
    result: list[dict] = []
    for row in rows:
        cell = {key: str(value).strip() for key, value in row.items()}
        email_key = cell.get("email", "").lower()
        if email_key in seen:
            continue
        seen.add(email_key)
        if "phone" in cell:
            cell["phone"] = _normalise_phone(cell["phone"])
        result.append(cell)
    return result
