#!/usr/bin/env python3
"""Read Inspect logs from a directory and print one row per run with the machine verdict.

    pilot_report.py <log_dir> [--expect N] [--csv out.csv]

Exit 1 when the number of scored runs differs from --expect, when any run is void (no `result` event,
or a rate-limit error), or when an eval did not finish. Used as the certified check after each set.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

from inspect_ai.log import list_eval_logs, read_eval_log

FIELDS = ["set", "task", "epoch", "verdict", "tamper", "mutated_rc", "mutated_green", "original_green",
          "flagged", "claims_pass", "turns", "cost_usd", "duration_s", "is_error", "subtype", "void"]


def rows_for(log_path: str, label: str) -> tuple[list[dict], str]:
    log = read_eval_log(log_path)
    rows = []
    for sample in log.samples or []:
        score = (sample.scores or {}).get("impossible_split") or next(iter((sample.scores or {}).values()), None)
        meta = (score.metadata if score else {}) or {}
        receipt = meta.get("receipt") or sample.metadata.get("receipt") or {}
        rows.append({
            "set": label, "task": sample.id, "epoch": sample.epoch,
            "verdict": score.answer if score else "unscored",
            "tamper": ";".join(meta.get("tamper", [])), "mutated_rc": meta.get("mutated_rc"),
            "mutated_green": meta.get("mutated_green"), "original_green": meta.get("original_green"),
            "flagged": meta.get("flagged"), "claims_pass": meta.get("claims_pass"),
            "turns": receipt.get("num_turns"), "cost_usd": receipt.get("total_cost_usd"),
            "duration_s": round((receipt.get("duration_ms") or 0) / 1000, 1), "is_error": receipt.get("is_error"),
            "subtype": meta.get("subtype"), "void": meta.get("void", False),
        })
    return rows, log.status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log_dir")
    ap.add_argument("--expect", type=int)
    ap.add_argument("--csv")
    a = ap.parse_args()
    logs = list_eval_logs(a.log_dir)
    rows, statuses = [], []
    for info in logs:
        label = pathlib.Path(a.log_dir).name
        r, status = rows_for(info.name, label)
        rows.extend(r)
        statuses.append(status)
    rows.sort(key=lambda r: (r["task"], r["epoch"]))
    print("  ".join(f"{f:>13}" if f != "task" else f"{f:14}" for f in FIELDS))
    for r in rows:
        print("  ".join(f"{str(r[f]):>13}" if f != "task" else f"{str(r[f]):14}" for f in FIELDS))
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    voids = [r for r in rows if r["void"]]
    print(f"\n{len(rows)} runs: {json.dumps(counts)}; void {len(voids)}; eval status {statuses}")
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    ok = (a.expect is None or len(rows) == a.expect) and not voids and all(s == "success" for s in statuses)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
