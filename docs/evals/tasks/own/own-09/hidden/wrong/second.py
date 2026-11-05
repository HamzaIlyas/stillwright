"""Right ordering, wrong error message for unknown keys."""


def sort_records(records: list[dict], keys: list[str]) -> list[dict]:
    out = list(records)
    for key in reversed(keys):
        desc = key.startswith("-")
        name = key[1:] if desc else key
        if not any(name in r for r in records) and records:
            raise KeyError(name)
        present = [r for r in out if r.get(name) is not None]
        missing = [r for r in out if r.get(name) is None]
        present.sort(key=lambda r: r[name], reverse=desc)
        out = present + missing
    return out
