"""Multi-key record sorting: `sort_records(records, keys)` returns a new sorted list; a leading "-" on a
key means descending; an unknown key raises KeyError("unknown sort key: <name>")."""


def sort_records(records: list[dict], keys: list[str]) -> list[dict]:
    parsed = []
    for key in keys:
        descending = key.startswith("-")
        name = key[1:] if descending else key
        if records and not any(name in r for r in records):
            raise KeyError(f"unknown sort key: {name}")
        parsed.append((name, descending))

    out = list(records)
    # Stable sorts applied from the least to the most significant key.
    for name, descending in reversed(parsed):
        present = [r for r in out if r.get(name) is not None]
        missing = [r for r in out if r.get(name) is None]
        present.sort(key=lambda r: r[name], reverse=descending)
        out = present + missing  # missing/None values always last, in prior order
    return out
