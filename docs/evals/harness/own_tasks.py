#!/usr/bin/env python3
"""Validator and manifest for the own task set (decision 2026-10-29 v3 section 5; pilot 3 design).

    validate <tasks_root> [--tasks id ...] [--skip-independent] [--reps 5]
        Per task: the shipped module fails visible and hidden; the oracle passes visible and hidden `reps`
        times; every wrong patch passes visible and fails hidden; the independent solution passes hidden;
        for a recipe-3 task the flaky test fails 3+ of 20 runs as shipped and 0 of 20 with the oracle.
        Exit 0 only when every task passes every check. Prints one line per check that fails.
    manifest <tasks_root>
        Writes manifest.json: per-task folder sha256 (hidden/ included), recipe, honest outcome, and the
        sha256 of a deterministic tar of all task folders (the archive hash that binds the runs, section 8).

Task folder layout: instruction.md, <module>.py (+ files), tests/test_visible.py, hidden/test_hidden.py,
hidden/oracle/<files>, hidden/wrong/<patch>.py, hidden/independent/<files>, task.json with
{"id", "recipe", "module", "protected_paths", "honest_outcome", "wrong_patches": {patch: target}, "flaky_test"?}.
Run under the harness python: uv run --python 3.12 --with pytest python3 own_tasks.py ...
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from verdicts import suite_green  # noqa: E402

GRADER = [sys.executable, "-I", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "pythonpath=.", "tests"]
SKIP = ("hidden", "__pycache__", ".pytest_cache", ".grade*")


@dataclasses.dataclass
class Result:
    task: str
    failures: list[str]
    details: dict

    @property
    def ok(self) -> bool:
        return not self.failures


def run_suite(task: pathlib.Path, test_file: pathlib.Path, patches: dict[str, pathlib.Path] | None = None, select: str | None = None) -> tuple[bool, str]:
    """Copy the task (without hidden/), apply patches (target relative path -> source file), make tests/ hold
    only `test_file`, run the grader. Returns (green, last line)."""
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "t"
        shutil.copytree(task, work, ignore=shutil.ignore_patterns(*SKIP))
        for target, src in (patches or {}).items():
            dest = work / target
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy(src, dest)
        shutil.rmtree(work / "tests", ignore_errors=True)
        (work / "tests").mkdir()
        shutil.copy(test_file, work / "tests" / test_file.name)
        cmd = GRADER + (["-k", select] if select else [])
        res = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=300)
        out = res.stdout + res.stderr
        last = out.strip().splitlines()[-1] if out.strip() else ""
        return suite_green(res.returncode, out), last


def oracle_patches(task: pathlib.Path, folder: str) -> dict[str, pathlib.Path]:
    root = task / "hidden" / folder
    return {str(p.relative_to(root)): p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def validate_task(task: pathlib.Path, reps: int = 5, skip_independent: bool = False) -> Result:
    meta = json.loads((task / "task.json").read_text())
    visible, hidden = task / "tests" / "test_visible.py", task / "hidden" / "test_hidden.py"
    failures, details = [], {}

    def check(name: str, cond: bool, info: str) -> None:
        details[name] = (cond, info)
        if not cond:
            failures.append(f"{meta['id']}: {name} ({info})")

    for required in (visible, hidden, task / "hidden" / "oracle", task / "instruction.md"):
        if not required.exists():
            return Result(meta["id"], [f"{meta['id']}: missing {required.relative_to(task)}"], {})
    g, info = run_suite(task, visible)
    check("shipped module fails visible with an assertion", (not g) and "failed" in info and "error" not in info, info)
    g, info = run_suite(task, hidden)
    check("shipped module fails hidden with an assertion", (not g) and "failed" in info and "error" not in info, info)
    oracle = oracle_patches(task, "oracle")
    g, info = run_suite(task, visible, oracle)
    check("oracle passes visible", g, info)
    for i in range(reps):
        g, info = run_suite(task, hidden, oracle)
        check(f"oracle passes hidden (rep {i + 1})", g, info)
        if not g:
            break
    wrong_dir = task / "hidden" / "wrong"
    patches = sorted(wrong_dir.glob("*.py")) if wrong_dir.exists() else []
    check("two wrong patches present", len(patches) >= 2, f"{len(patches)} found")
    for patch in patches:
        target = meta.get("wrong_patches", {}).get(patch.name, meta["module"])
        g, info = run_suite(task, visible, {target: patch})
        check(f"wrong patch {patch.name} passes visible", g, info)
        g, info = run_suite(task, hidden, {target: patch})
        check(f"wrong patch {patch.name} fails hidden", not g, info)
    if not skip_independent:
        ind = task / "hidden" / "independent"
        if not ind.exists() or not any(ind.rglob("*.py")):
            check("independent solution present", False, "hidden/independent missing")
        else:
            g, info = run_suite(task, hidden, oracle_patches(task, "independent"))
            check("independent solution passes hidden", g, info)
    flaky = meta.get("flaky_test")
    if flaky:
        shipped = sum(1 for _ in range(20) if not run_suite(task, visible, select=flaky)[0])
        check("flaky test fails 3+ of 20 as shipped", shipped >= 3, f"{shipped}/20 failed")
        check("flaky test passes 3+ of 20 as shipped", shipped <= 17, f"{shipped}/20 failed")
        fixed = sum(1 for _ in range(20) if not run_suite(task, visible, oracle, select=flaky)[0])
        check("flaky test passes 20 of 20 with the oracle", fixed == 0, f"{fixed}/20 failed")
    return Result(meta["id"], failures, details)


def folder_sha256(folder: pathlib.Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(str(p.relative_to(folder)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def archive_sha256(root: pathlib.Path, ids: list[str]) -> str:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for tid in ids:
            for p in sorted((root / tid).rglob("*")):
                if p.is_file() and "__pycache__" not in p.parts:
                    info = tarfile.TarInfo(str(p.relative_to(root)))
                    data = p.read_bytes()
                    info.size, info.mtime, info.uid, info.gid, info.mode = len(data), 0, 0, 0, 0o644
                    tar.addfile(info, io.BytesIO(data))
    return hashlib.sha256(buf.getvalue()).hexdigest()


def task_dirs(root: pathlib.Path, only: list[str] | None) -> list[pathlib.Path]:
    dirs = sorted(p for p in root.iterdir() if (p / "task.json").exists())
    return [d for d in dirs if not only or d.name in only]


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("root")
    v.add_argument("--tasks", nargs="*")
    v.add_argument("--skip-independent", action="store_true")
    v.add_argument("--reps", type=int, default=5)
    m = sub.add_parser("manifest")
    m.add_argument("root")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    if a.cmd == "validate":
        bad = 0
        for d in task_dirs(root, a.tasks):
            r = validate_task(d, reps=a.reps, skip_independent=a.skip_independent)
            print(f"{r.task:8} {'ok' if r.ok else 'FAIL'}  {sum(1 for c in r.details.values() if c[0])}/{len(r.details)} checks")
            for f in r.failures:
                print("   ", f)
            bad += not r.ok
        return 1 if bad else 0
    dirs = task_dirs(root, None)
    tasks = []
    for d in dirs:
        meta = json.loads((d / "task.json").read_text())
        tasks.append({"id": meta["id"], "recipe": meta["recipe"], "honest_outcome": meta["honest_outcome"], "folder_sha256": folder_sha256(d)})
    manifest = {"split": "own", "tasks": tasks, "archive_sha256": archive_sha256(root, [d.name for d in dirs])}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(tasks)} tasks, archive sha256 {manifest['archive_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
