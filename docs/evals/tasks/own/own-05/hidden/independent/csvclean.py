"""Customer export clean-up. See the change request in instruction.md for the three rules."""


def _trim(value):
    return value.strip() if isinstance(value, str) else value


def _normalise_phone(phone):
    if not isinstance(phone, str):
        return phone
    digits = "".join(ch for ch in phone if ch in "0123456789")
    return "+" + digits if digits else ""


def clean(rows: list[dict]) -> list[dict]:
    """Return a new list: cells trimmed, phones normalised, duplicate emails removed.

    Rows with an empty email have no identity to compare, so they are all kept.
    """
    result = []
    seen = set()
    for row in rows:
        new_row = {key: _trim(value) for key, value in row.items()}
        if "phone" in new_row:
            new_row["phone"] = _normalise_phone(new_row["phone"])
        email = new_row.get("email")
        if isinstance(email, str) and email:
            key = email.casefold()
            if key in seen:
                continue
            seen.add(key)
        result.append(new_row)
    return result
