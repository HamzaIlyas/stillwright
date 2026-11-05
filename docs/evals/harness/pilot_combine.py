#!/usr/bin/env python3
"""Combine per-set CSVs from pilot_report.py into one results.csv, numbering epochs by set.

    pilot_combine.py <out.csv> <set1.csv> <set2.csv> ...

Each set is one Inspect eval with one epoch, so the epoch column is 1 in every file; here the set label
(set1, set2, set3, sorted, whatever the argument order) gives the epoch, which is the key the hand labels use.
Every row of a file must carry the same set label, or the script stops.
"""
import csv
import sys


def main() -> int:
    out, sets = sys.argv[1], sys.argv[2:]
    by_set = {}
    for path in sets:
        with open(path, newline="") as f:
            file_rows = list(csv.DictReader(f))
        labels = {r["set"] for r in file_rows}
        if len(labels) != 1:
            raise SystemExit(f"{path}: expected one set label, found {sorted(labels)}")
        by_set[labels.pop()] = file_rows
    rows = []
    for n, label in enumerate(sorted(by_set), 1):
        rows.extend({**r, "epoch": str(n)} for r in by_set[label])
    rows.sort(key=lambda r: (r["task"], int(r["epoch"])))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows from {len(sets)} sets -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
