#!/usr/bin/env python3
"""Run every `sw ...` line inside fenced code blocks of the given Markdown files against the
sw binary, in a throwaway STILLWRIGHT_HOME. Docs that drift from the CLI fail CI.

Lines are run in order within one file, so later commands may depend on earlier ones.
A line ending in `# may fail` is allowed a non-zero exit (used to show error messages)."""
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def binary() -> str:
    if os.environ.get("SW_BIN"):
        return os.environ["SW_BIN"]
    for build in ("release", "debug"):
        for name in ("sw", "sw.exe"):
            p = ROOT / "target" / build / name
            if p.exists():
                return str(p)
    sys.exit("sw binary not found: cargo build --release, or set SW_BIN")


def commands(markdown: str):
    in_block = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_block = not in_block
            continue
        if in_block and line.strip().startswith("sw "):
            yield line.strip()


def main(paths) -> int:
    sw = binary()
    failures = 0
    for path in paths:
        text = pathlib.Path(path).read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, "STILLWRIGHT_HOME": home}
            for cmd in commands(text):
                may_fail = cmd.endswith("# may fail")
                argv = shlex.split(cmd[: -len("# may fail")] if may_fail else cmd)[1:]
                result = subprocess.run([sw, *argv], env=env, capture_output=True, text=True, cwd=home)
                ok = result.returncode == 0 or may_fail
                print(f"{'ok  ' if ok else 'FAIL'} {path}: {cmd}")
                if not ok:
                    print(result.stderr.strip() or result.stdout.strip())
                    failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or sorted(str(p) for p in (ROOT / "docs").glob("*.md"))))
