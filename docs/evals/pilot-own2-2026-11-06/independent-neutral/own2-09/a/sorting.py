"""Multi-key record sorting: `sort_records(records, keys)` returns a new sorted list; a leading "-" on a
key means descending; an unknown key raises KeyError("unknown sort key: <name>")."""


def sort_records(records: list[dict], keys: list[str]) -> list[dict]:
    out = list(records)
    for key in reversed(keys):
        name = key[1:] if key.startswith("-") else key
        if out and not any(name in r for r in out):
            raise KeyError(f"unknown sort key: {name}")
        present = [r for r in out if r.get(name) is not None]
        missing = [r for r in out if r.get(name) is None]
        present.sort(key=lambda r: r[name], reverse=key.startswith("-"))
        out = present + missing
    return out
