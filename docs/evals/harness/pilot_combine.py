#!/usr/bin/env python3
"""Combine per-set CSVs from pilot_report.py into one results.csv, numbering epochs by set.

    pilot_combine.py <out.csv> <set1.csv> <set2.csv> ...

Each set is one Inspect eval with one epoch, so the epoch column is 1 in every file; here the set's
position (1, 2, 3) becomes the epoch, which is the key the hand labels use.
"""
import csv
import sys


def main() -> int:
    out, sets = sys.argv[1], sys.argv[2:]
    rows = []
    for n, path in enumerate(sets, 1):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                rows.append({**r, "epoch": str(n)})
    rows.sort(key=lambda r: (r["task"], int(r["epoch"])))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows from {len(sets)} sets -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
