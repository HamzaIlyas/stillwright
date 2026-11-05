"""None-last works for single keys, but descending with several keys breaks and unknown keys pass silently."""


def sort_records(records: list[dict], keys: list[str]) -> list[dict]:
    out = list(records)
    for key in reversed(keys):
        desc = key.startswith("-")
        name = key.lstrip("-")
        out.sort(key=lambda r: (r.get(name) is None, r.get(name) if r.get(name) is not None else 0), reverse=desc)
        if desc:
            nones = [r for r in out if r.get(name) is None]
            out = [r for r in out if r.get(name) is not None] + nones
    return out
