#!/usr/bin/env python3
"""Print a sha256 over the grader interpreter's importable files: path, size and mtime of everything under
every site-packages directory on sys.path (uv's ephemeral environments layer one over another) plus
directories named by .pth files and its bin directory, __pycache__ excluded. Same environment, same output, in
any process. Run before and after the agent's turn; a difference means the environment the grader runs
in was changed during the run."""
import hashlib
import os
import sys
import sysconfig


def roots() -> list[str]:
    paths = sysconfig.get_paths()
    found = {paths["purelib"], paths["platlib"], os.path.dirname(sys.executable)}
    found.update(p for p in sys.path if os.path.isdir(p) and "site-packages" in p)
    for base in (paths["purelib"], paths["platlib"]):
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            if name.endswith(".pth"):
                with open(os.path.join(base, name), encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith(("#", "import ")) and os.path.isdir(line):
                            found.add(line)
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
                h.update(f"{p}:{st.st_size}:{st.st_mtime_ns}\n".encode())
    return h.hexdigest()


if __name__ == "__main__":
    print(fingerprint())
