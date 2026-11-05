"""Multi-key record sorting: `sort_records(records, keys)` returns a new sorted list; a leading "-" on a
key means descending; an unknown key raises KeyError("unknown sort key: <name>").

Records whose value for a key is missing or None always come last for that key, in both directions.
The sort is stable. A key is "unknown" when no record has it at all."""


def sort_records(records: list[dict], keys: list[str]) -> list[dict]:
    parsed = [(k[1:], True) if k.startswith("-") else (k, False) for k in keys]
    for name, _ in parsed:
        if records and not any(name in r for r in records):
            raise KeyError(f"unknown sort key: {name}")

    out = list(records)
    for name, descending in reversed(parsed):
        present = [r for r in out if r.get(name) is not None]
        missing = [r for r in out if r.get(name) is None]
        present.sort(key=lambda r: r[name], reverse=descending)
        out = present + missing
    return out
