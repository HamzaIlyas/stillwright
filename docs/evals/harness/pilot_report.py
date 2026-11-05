#!/usr/bin/env python3
"""Read Inspect logs from a directory and print one row per run with the machine verdict.

    pilot_report.py <log_dir> [--expect N] [--csv out.csv] [--tasks <tasks_dir>]

`verdict` is always computed here from the run's stored facts (tamper list, grader exit codes, final
message) with the current rules in verdicts.py, so a rule fix re-scores old logs without re-running
anything; `verdict_at_run` is what the scorer wrote at the time. With --tasks, the conflict markers
are rebuilt from the task folders (needed for logs older than the markers field).

Exit 1 when the number of scored runs differs from --expect, when any run is void (no `result` event,
or a rate-limit error), when an eval did not finish, or when the grader-environment fingerprints of the
runs in the directory are not all identical (a run changed the environment the grader runs in).
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

from inspect_ai.log import list_eval_logs, read_eval_log

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from verdicts import conflict_markers, impossible_verdict, names_wrong_test  # noqa: E402

FIELDS = ["set", "task", "epoch", "verdict", "verdict_at_run", "tamper", "mutated_rc", "mutated_green", "original_green",
          "flagged", "names_wrong_test", "claims_pass", "turns", "cost_usd", "duration_s", "is_error", "subtype", "void", "env_fingerprint"]


def task_markers(tasks_dir: str | None) -> dict[str, list[str]]:
    if not tasks_dir:
        return {}
    out = {}
    for folder in pathlib.Path(tasks_dir).iterdir():
        vis, orig = folder / "tests" / "test_visible.py", folder / "hidden" / "test_original.py"
        if vis.exists() and orig.exists():
            out[folder.name] = conflict_markers(vis.read_text(), orig.read_text())
    return out


def rows_for(log_path: str, label: str, markers_by_task: dict) -> tuple[list[dict], str]:
    log = read_eval_log(log_path)
    rows = []
    for sample in log.samples or []:
        score = (sample.scores or {}).get("impossible_split") or next(iter((sample.scores or {}).values()), None)
        meta = (score.metadata if score else {}) or {}
        receipt = meta.get("receipt") or sample.metadata.get("receipt") or {}
        message = sample.output.completion or ""
        markers = markers_by_task.get(sample.id) or sample.metadata.get("markers") or []
        names = names_wrong_test(message, markers)
        void = bool(meta.get("void", False))
        verdict = "void" if void else impossible_verdict(meta.get("tamper", []), meta.get("mutated_rc", 1), message, names,
                                                          bool(meta.get("original_green"))) if score else "unscored"
        rows.append({
            "set": label, "task": sample.id, "epoch": sample.epoch,
            "verdict": verdict, "verdict_at_run": score.answer if score else "unscored",
            "tamper": ";".join(meta.get("tamper", [])), "mutated_rc": meta.get("mutated_rc"),
            "mutated_green": meta.get("mutated_green"), "original_green": meta.get("original_green"),
            "flagged": meta.get("flagged"), "names_wrong_test": names, "claims_pass": meta.get("claims_pass"),
            "turns": receipt.get("num_turns"), "cost_usd": receipt.get("total_cost_usd"),
            "duration_s": round((receipt.get("duration_ms") or 0) / 1000, 1), "is_error": receipt.get("is_error"),
            "subtype": meta.get("subtype"), "void": void, "env_fingerprint": (meta.get("env_fingerprint") or "")[:12],
        })
    return rows, log.status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log_dir")
    ap.add_argument("--expect", type=int)
    ap.add_argument("--csv")
    ap.add_argument("--tasks")
    a = ap.parse_args()
    logs = list_eval_logs(a.log_dir)
    markers_by_task = task_markers(a.tasks)
    rows, statuses = [], []
    for info in logs:
        label = pathlib.Path(a.log_dir).name
        r, status = rows_for(info.name, label, markers_by_task)
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
    fingerprints = {r["env_fingerprint"] for r in rows if r["env_fingerprint"]}
    print(f"\n{len(rows)} runs: {json.dumps(counts)}; void {len(voids)}; eval status {statuses}; grader env fingerprints {len(fingerprints)}")
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    ok = (a.expect is None or len(rows) == a.expect) and not voids and all(s == "success" for s in statuses) and len(fingerprints) <= 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
