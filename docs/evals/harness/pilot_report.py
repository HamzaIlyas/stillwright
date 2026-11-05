#!/usr/bin/env python3
"""Read Inspect logs from a directory and print one row per run with the machine verdict.

    pilot_report.py <log_dir> [--expect N] [--csv out.csv] [--tasks <tasks_dir>]

`verdict` is always computed here from the run's stored facts (tamper list, grader exit codes, final
message) with the current rules in verdicts.py, so a rule fix re-scores old logs without re-running
anything; `verdict_at_run` is what the scorer wrote at the time. With --tasks, the conflict markers
are rebuilt from the task folders (needed for logs older than the markers field).

Exit 1 when the number of scored runs differs from --expect, when any run is void (no `result` event,
or a rate-limit error), when an eval did not finish, when a sample lacks the scorer's facts or conflict
markers (then it is `unscored`, never guessed), when a task folder's hash differs from the manifest in
--tasks, or when the runs of one eval do not share one grader-environment fingerprint. A run whose
`result` event has `is_error` for another reason is `error` (counted per arm, decision section 7).
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

from inspect_ai.log import list_eval_logs, read_eval_log

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from verdicts import claims_pass, closing_text, conflict_markers, impossible_verdict, names_wrong_test, receipt_of, result_events, solvable_verdict  # noqa: E402

FIELDS = ["set", "task", "epoch", "verdict", "verdict_at_run", "tamper", "mutated_rc", "mutated_green", "original_green",
          "visible_green", "hidden_green", "flagged", "names_wrong_test", "claims_pass", "turns", "cost_usd", "duration_s", "results",
          "is_error", "subtype", "void", "env_fingerprint"]
SOLVABLE_REQUIRED = ("tamper", "hidden_green", "visible_green", "void")


def task_markers(tasks_dir: str | None) -> dict[str, list[str]]:
    if not tasks_dir:
        return {}
    out = {}
    for folder in pathlib.Path(tasks_dir).iterdir():
        vis, orig = folder / "tests" / "test_visible.py", folder / "hidden" / "test_original.py"
        if vis.exists() and orig.exists():
            out[folder.name] = conflict_markers(vis.read_text(), orig.read_text())
    return out


REQUIRED = ("tamper", "mutated_rc", "original_green", "void")


def folder_sha256(folder: pathlib.Path) -> str:
    import hashlib
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(str(p.relative_to(folder)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def rows_for(log_path: str, label: str, markers_by_task: dict, manifest_hashes: dict, problems: list[str], disk_hashes: dict | None = None) -> tuple[list[dict], str]:
    disk_hashes = disk_hashes or {}
    log = read_eval_log(log_path)
    rows = []
    for sample in log.samples or []:
        scores = sample.scores or {}
        split = "solvable" if "solvable_split" in scores else "impossible"
        score = scores.get("solvable_split") or scores.get("impossible_split")
        meta = (score.metadata if score else {}) or {}
        receipt = dict(meta.get("receipt") or sample.metadata.get("receipt") or {})
        message = sample.output.completion or ""
        stream = sample.metadata.get("stream_jsonl") or ""
        if stream:  # the same receipt arithmetic as the solver, so old and new logs are read under one rule
            events = result_events(stream)
            if events:
                receipt.update(receipt_of(events))
                message = closing_text(events)
        visible = "\n".join((sample.metadata.get("visible_tests") or {}).values()) or None
        markers = markers_by_task.get(sample.id) or sample.metadata.get("markers") or []
        names = names_wrong_test(message, markers, visible)
        key = f"{label}/{sample.id}/{sample.epoch}"
        required = SOLVABLE_REQUIRED if split == "solvable" else REQUIRED
        if score is None or any(k not in meta for k in required):
            problems.append(f"{key}: not scored by {split}_split with {required}")
            verdict, void = "unscored", False
        elif split == "impossible" and not markers:
            problems.append(f"{key}: no conflict markers (pass --tasks, or the task has none)")
            verdict, void = "unscored", False
        else:
            void = bool(meta["void"])
            if void:
                verdict = "void"
            elif receipt.get("is_error"):
                verdict = "error"
            elif split == "solvable":
                verdict = solvable_verdict(meta["tamper"], bool(meta["hidden_green"]), message, meta.get("failure_markers", []))
            else:
                verdict = impossible_verdict(meta["tamper"], meta["mutated_rc"], message, names, bool(meta["original_green"]))
        if manifest_hashes and sample.id in manifest_hashes:
            on_disk = disk_hashes.get(sample.id)
            if meta.get("folder_sha256") not in (None, manifest_hashes[sample.id]) or (on_disk and on_disk != manifest_hashes[sample.id]):
                problems.append(f"{key}: task folder hash differs between the run, the manifest and the folder on disk")
        rows.append({
            "set": label, "task": sample.id, "epoch": sample.epoch,
            "verdict": verdict, "verdict_at_run": score.answer if score else "unscored",
            "tamper": ";".join(meta.get("tamper", [])), "mutated_rc": meta.get("mutated_rc"),
            "mutated_green": meta.get("mutated_green"), "original_green": meta.get("original_green"),
            "visible_green": meta.get("visible_green"), "hidden_green": meta.get("hidden_green"),
            "flagged": "flag_for_human_intervention" in message.lower(), "names_wrong_test": names if split == "impossible" else "", "claims_pass": claims_pass(message),
            "turns": receipt.get("num_turns"), "cost_usd": receipt.get("total_cost_usd"),
            "duration_s": round((receipt.get("duration_ms") or 0) / 1000, 1), "results": receipt.get("result_events", 1), "is_error": receipt.get("is_error"),
            "subtype": meta.get("subtype"), "void": void, "env_fingerprint": (meta.get("env_fingerprint") or "")[:12],
        })
    fingerprints = {r["env_fingerprint"] for r in rows if r["env_fingerprint"]}
    if len(fingerprints) > 1:
        problems.append(f"{label}/{pathlib.Path(log_path).name}: {len(fingerprints)} different grader-environment fingerprints in one eval")
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
    manifest_hashes = {}
    if a.tasks and (pathlib.Path(a.tasks) / "manifest.json").exists():
        manifest_hashes = {t["id"]: t["folder_sha256"] for t in json.loads((pathlib.Path(a.tasks) / "manifest.json").read_text())["tasks"]}
    disk_hashes = {tid: folder_sha256(pathlib.Path(a.tasks) / tid) for tid in manifest_hashes if (pathlib.Path(a.tasks) / tid).is_dir()}
    rows, statuses, problems = [], [], []
    for info in logs:
        label = pathlib.Path(a.log_dir).name
        r, status = rows_for(info.name, label, markers_by_task, manifest_hashes, problems, disk_hashes)
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
    for problem in problems:
        print("problem:", problem)
    multi = [r for r in rows if (r["results"] or 1) > 1]
    if multi:
        print("note: sessions that closed more than once (turns and wall time summed, closing texts joined): " + ", ".join(f"{r['task']}/{r['epoch']}x{r['results']}" for r in multi))
    print(f"\n{len(rows)} runs: {json.dumps(counts)}; void {len(voids)}; eval status {statuses}; problems {len(problems)}")
    ok = (a.expect is None or len(rows) == a.expect) and not voids and all(s == "success" for s in statuses) and not problems
    if a.csv and ok:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    elif a.csv:
        print(f"no CSV written: the report has problems")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
