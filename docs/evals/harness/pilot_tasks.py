#!/usr/bin/env python3
"""Pick and verify the pilot task set from an exported ImpossibleBench pool.

    select <pool_split_dir> <out_dir> [--seed 20261105] [--n 10]
        Sorted task ids, one seeded shuffle; walking it, the first n tasks whose visible and original test
        files both parse, that carry conflict markers, and whose untouched stub fails the visible suite with
        an assertion failure (not a collection error) are the pilot set (copied to <out_dir>/<id>), the next one is the dry-run task
        (copied to <out_dir>/../dry/<id>). Tasks skipped for a syntax error are listed in the manifest.
        Writes <out_dir>/manifest.json.
    verify <out_dir>
        For every task in the manifest: folder hash unchanged, visible and original tests differ, test
        hashes match task.json, both test files parse, and the untouched stub fails the visible suite under
        the grader command.
        Exit 0 only if all hold.

Run under the harness python: uv run --python 3.12 --with pytest python3 pilot_tasks.py ...
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile

from verdicts import conflict_markers, suite_green

GRADER = [sys.executable, "-I", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "pythonpath=.", "tests"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def folder_sha256(folder: pathlib.Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(str(p.relative_to(folder)).encode("utf-8"))
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def task_ids(pool: pathlib.Path) -> list[str]:
    return sorted(p.name for p in pool.iterdir() if (p / "task.json").exists())


def tests_parse(task: pathlib.Path) -> bool:
    for rel in ("tests/test_visible.py", "hidden/test_original.py"):
        try:
            ast.parse((task / rel).read_text())
        except SyntaxError:
            return False
    return True


def markers_of(task: pathlib.Path) -> list[str]:
    return conflict_markers((task / "tests" / "test_visible.py").read_text(), (task / "hidden" / "test_original.py").read_text())


def select(pool: pathlib.Path, out: pathlib.Path, seed: int, n: int) -> int:
    ids = task_ids(pool)
    order = random.Random(seed).sample(ids, len(ids))
    chosen, skipped, no_markers, not_failing = [], [], [], []
    for tid in order:
        if not tests_parse(pool / tid):
            skipped.append(tid)
        elif not markers_of(pool / tid):
            no_markers.append(tid)  # "named the wrong test" could never be true: honest unreachable
        elif not stub_fails(pool / tid)[0]:
            not_failing.append(tid)  # collection error or no assertion failure: not a contradiction task
        else:
            chosen.append(tid)
        if len(chosen) == n + 1:
            break
    chosen, dry = chosen[:n], chosen[n]
    out.mkdir(parents=True, exist_ok=True)
    dry_dir = out.parent / "dry"
    dry_dir.mkdir(parents=True, exist_ok=True)
    for tid in chosen:
        shutil.copytree(pool / tid, out / tid, dirs_exist_ok=True)
    shutil.copytree(pool / dry, dry_dir / dry, dirs_exist_ok=True)
    tasks = []
    for tid in sorted(chosen):
        meta = json.loads((out / tid / "task.json").read_text())
        tasks.append({"id": tid, "folder_sha256": folder_sha256(out / tid),
                      "visible_test_sha256": meta["visible_test_sha256"], "original_test_sha256": meta["original_test_sha256"]})
    split = json.loads((out / chosen[0] / "task.json").read_text())["split"]
    manifest = {"seed": seed, "pool_dir": pool.name, "pool_size": len(ids), "pool_ids_sha256": sha256_bytes("\n".join(ids).encode()),
                "split": split, "tasks": tasks, "dry_task": {"id": dry, "folder_sha256": folder_sha256(dry_dir / dry)},
                "skipped_syntax_error": skipped, "skipped_no_markers": no_markers, "skipped_stub_not_failing": not_failing}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"pilot set ({n}): {' '.join(sorted(chosen))}\ndry-run task: {dry}\nskipped (syntax error in a test file): {skipped}\nskipped (no conflict markers): {no_markers}\nskipped (stub does not fail with an assertion): {not_failing}\nmanifest: {out / 'manifest.json'}")
    return 0


def stub_fails(task: pathlib.Path) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "t"
        shutil.copytree(task, work, ignore=shutil.ignore_patterns("hidden", "__pycache__"))
        res = subprocess.run(GRADER, cwd=work, capture_output=True, text=True, timeout=120)
        out = res.stdout + res.stderr
        last = out.strip().splitlines()[-1] if out.strip() else ""
        # a real assertion failure, not a collection error, a skip or an exit 0
        return (res.returncode != 0 and "failed" in last and "error" not in last and not suite_green(res.returncode, out)), last


def verify(out: pathlib.Path) -> int:
    manifest = json.loads((out / "manifest.json").read_text())
    bad = 0
    for entry in manifest["tasks"]:
        tid = entry["id"]
        task = out / tid
        meta = json.loads((task / "task.json").read_text())
        visible = (task / "tests" / "test_visible.py").read_bytes()
        original = (task / "hidden" / "test_original.py").read_bytes()
        checks = {
            "folder hash": folder_sha256(task) == entry["folder_sha256"],
            "tests differ": meta["tests_differ"] and visible != original,
            "visible hash": sha256_bytes(visible) == meta["visible_test_sha256"],
            "original hash": sha256_bytes(original) == meta["original_test_sha256"],
            "tests parse": tests_parse(task),
            "has markers": bool(markers_of(task)),
        }
        fails, last = stub_fails(task)
        checks["stub fails visible"] = fails
        failed = [k for k, v in checks.items() if not v]
        bad += bool(failed)
        print(f"{tid:14} {'ok' if not failed else 'FAIL ' + ', '.join(failed):28} {last}")
    print(f"{len(manifest['tasks']) - bad}/{len(manifest['tasks'])} tasks verified")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("pool")
    s.add_argument("out")
    s.add_argument("--seed", type=int, default=20261105)
    s.add_argument("--n", type=int, default=10)
    v = sub.add_parser("verify")
    v.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "select":
        return select(pathlib.Path(a.pool), pathlib.Path(a.out), a.seed, a.n)
    return verify(pathlib.Path(a.out))


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    raise SystemExit(main())
