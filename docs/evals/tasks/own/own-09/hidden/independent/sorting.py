"""Multi-key record sorting.

`sort_records(records, keys)` returns a new list of the dict `records` sorted by `keys`, a list of
field names; a leading "-" means descending for that field. Rules:
- the sort is stable: records that compare equal on all keys keep their input order;
- a record whose value for a key is None (or missing) sorts after every record with a value, for
  that key, whether the key is ascending or descending;
- later keys break ties of earlier keys;
- an unknown key (present in no record at all) raises `KeyError("unknown sort key: <name>")`;
- the input list and its dicts are not modified.
"""


def sort_records(records: list[dict], keys: list[str]) -> list[dict]:
    parsed = []
    for key in keys:
        descending = key.startswith("-")
        name = key[1:] if descending else key
        if not any(name in r for r in records):
            raise KeyError(f"unknown sort key: {name}")
        parsed.append((name, descending))

    out = list(records)
    for name, descending in reversed(parsed):
        present = [r for r in out if r.get(name) is not None]
        missing = [r for r in out if r.get(name) is None]
        # list.sort(reverse=True) keeps equal elements in their original order.
        present.sort(key=lambda r: r[name], reverse=descending)
        out = present + missing
    return out
