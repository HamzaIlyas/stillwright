"""Customer export clean-up."""
def _phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return "+" + digits if digits else ""


def clean(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for row in rows:
        new = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
        new["phone"] = _phone(new.get("phone", ""))
        key = new.get("email", "").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(new)
    return out
