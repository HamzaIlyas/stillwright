#!/usr/bin/env python3
"""Print a sha256 over what the grader interpreter can import: relative path, size, mtime and ctime of every
file under every site-packages directory on sys.path (uv's ephemeral environments layer one over another),
directories named by .pth files, the standard library (with lib-dynload, where `sitecustomize.py` lives),
the venv bin directory and the real interpreter's directory; __pycache__ excluded. Paths are hashed relative
to their root, so the output does not depend on the process; it does depend on file timestamps, and a new uv
ephemeral environment has new ones, so fingerprints compare within one `uv run` (one Inspect eval), never
across evals. Run before and after the agent's turn; a difference means the environment the grader runs in
changed during the run.
Not covered: an in-place edit that keeps size, mtime and ctime (ctime cannot be set with utime), and the
dynamic libraries the interpreter loads from outside these directories."""
import hashlib
import os
import sys
import sysconfig


def roots() -> list[str]:
    paths = sysconfig.get_paths()
    real = os.path.realpath(sys.executable)
    found = {paths["purelib"], paths["platlib"], os.path.dirname(sys.executable), paths["stdlib"], paths["platstdlib"],
             os.path.dirname(real), os.path.join(paths["stdlib"], "lib-dynload")}
    found.update(p for p in sys.path if os.path.isdir(p) and "site-packages" in p)
    found = {os.path.realpath(p) for p in found if os.path.isdir(p)}
    for base in (paths["purelib"], paths["platlib"]):
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            if name.endswith(".pth"):
                with open(os.path.join(base, name), encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith(("#", "import ")) and os.path.isdir(line):
                            found.add(os.path.realpath(line))
    return sorted(found)


def fingerprint() -> str:
    h = hashlib.sha256()
    for root in roots():
        for r, dirs, files in os.walk(root):
            dirs.sort()
            if "__pycache__" in r:
                continue
            for f in sorted(files):
                p = os.path.join(r, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                # path relative to its root: uv's ephemeral environments get a new prefix per invocation
                h.update(f"{os.path.basename(root)}/{os.path.relpath(p, root)}:{st.st_size}:{st.st_mtime_ns}:{st.st_ctime_ns}\n".encode())
    return h.hexdigest()


if __name__ == "__main__":
    print(fingerprint())
