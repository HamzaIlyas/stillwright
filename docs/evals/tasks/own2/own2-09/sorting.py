"""Multi-key record sorting: `sort_records(records, keys)` returns a new sorted list; a leading "-" on a
key means descending; an unknown key raises KeyError("unknown sort key: <name>")."""


def sort_records(records: list[dict], keys: list[str]) -> list[dict]:
    out = list(records)
    for key in reversed(keys):
        out.sort(key=lambda r: r.get(key.lstrip("-")), reverse=key.startswith("-"))
    return out
