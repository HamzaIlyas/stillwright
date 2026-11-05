"""Only rule 1: trims cells; the phone and the duplicates are left alone."""


def clean(rows: list[dict]) -> list[dict]:
    return [{k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()} for row in rows]
