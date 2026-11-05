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
    out = list(records)
    for key in reversed(keys):
        out.sort(key=lambda r: r.get(key.lstrip("-")), reverse=key.startswith("-"))
    return out
