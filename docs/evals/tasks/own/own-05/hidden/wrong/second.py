"""Rules 1 and 2, but duplicates are matched case-sensitively and before trimming."""


def _phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return "+" + digits if digits else ""


def clean(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for row in rows:
        if row.get("email") in seen:
            continue
        seen.add(row.get("email"))
        new = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
        new["phone"] = _phone(new.get("phone", ""))
        out.append(new)
    return out
