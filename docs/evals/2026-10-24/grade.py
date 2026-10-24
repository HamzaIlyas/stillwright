#!/usr/bin/env python3
"""Objective grading of the six eval runs. Prints a table and writes results.json.
Assertions a model cannot game: a script runs the tests, counts words, checks facts,
checks the report length, and looks for a run log with a passed check."""
import json
import pathlib
import re
import subprocess

E = pathlib.Path(__file__).resolve().parent
FACTS = ["2021", "Lahore", "400", "50"]
TRUTH = {"version": "0.1.1", "date": "2026-10-24"}


def report(run):
    p = run / "REPORT.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def lines(text):
    return [l for l in text.strip().splitlines() if l.strip()]


def task_done(task, run):
    if task == "code":
        r = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests"], cwd=run, capture_output=True, text=True)
        tests_untouched = (run / "tests/test_pricing.py").read_text() == (E / "fixtures/code/tests/test_pricing.py").read_text()
        return r.returncode == 0 and tests_untouched, f"unittest rc={r.returncode}, tests untouched={tests_untouched}"
    if task == "writing":
        p = run / "rewrite.md"
        if not p.exists():
            return False, "no rewrite.md"
        t = p.read_text()
        words = len(t.split())
        missing = [f for f in FACTS if f not in t]
        return words <= 80 and not missing, f"{words} words, missing facts={missing}"
    if task == "research":
        t = report(run)
        ok = TRUTH["version"] in t and TRUTH["date"] in t and "pypi.org" in t and "github.com/HamzaIlyas/stillwright" in t
        return ok, f"has version={TRUTH['version'] in t}, date={TRUTH['date'] in t}, pypi url={'pypi.org' in t}, github url={'github.com/HamzaIlyas/stillwright' in t}"


def evidence_in_report(task, run):
    t = report(run)
    if task == "code":
        return bool(re.search(r"Ran \d+ tests|OK\b|5 tests", t)), "quotes test run output"
    if task == "writing":
        return bool(re.search(r"\b\d{1,2} words\b", t)), "states the word count"
    if task == "research":
        return t.count("http") >= 2, "at least two URLs"


def run_logged(run):
    home = run / ".sw-home"
    logs = list(home.glob("runs/*/log.jsonl"))
    plans = list(home.glob("runs/*/plan.md"))
    passed = False
    for log in logs:
        for line in log.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("result") == "pass" and "step" in e:
                passed = True
    return bool(logs and plans and passed), f"plans={len(plans)} logs={len(logs)} pass_logged={passed}"


def main():
    results = {}
    for task in ("code", "writing", "research"):
        for mode in ("with", "without"):
            run = E / "runs" / f"{task}-{mode}"
            done, d1 = task_done(task, run)
            ev, d2 = evidence_in_report(task, run)
            short = len(lines(report(run))) <= 5
            logged, d3 = run_logged(run)
            results[f"{task}-{mode}"] = {
                "task_done": done, "task_done_detail": d1,
                "evidence_in_report": ev, "evidence_detail": d2,
                "report_5_lines_or_fewer": short, "report_lines": len(lines(report(run))),
                "run_logged_with_pass": logged, "log_detail": d3,
            }
    (E / "results.json").write_text(json.dumps(results, indent=2))
    print(f"{'run':18} {'done':5} {'evidence':8} {'<=5 lines':9} {'logged':6}")
    for k, v in results.items():
        print(f"{k:18} {str(v['task_done']):5} {str(v['evidence_in_report']):8} {str(v['report_5_lines_or_fewer']):9} {str(v['run_logged_with_pass']):6}")


if __name__ == "__main__":
    main()
