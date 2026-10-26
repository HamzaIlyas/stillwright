#!/usr/bin/env python3
"""A/B cost harness: run task folders through `claude -p` with and without something, keep receipts.

Default "something" is the Stillwright plugin from this working tree. Any other change (a hook,
a plugin, a setting) can be tested by passing extra CLI arguments for one side:
    --with-extra '--plugin-dir /path/to/other-plugin' --without-extra ''
Receipts come from Claude Code itself (`total_cost_usd`, tokens by model), never estimated.

Each run is one headless Claude Code session on a fresh copy of a task. The JSON result gives
`total_cost_usd` and per-model token usage, so cost is measured in money, not estimated.
Both sides use the same account configuration; the "without" side disables the Stillwright
plugin for that session only.

    python3 run_eval.py <fixtures_dir> <out_dir> [--tasks code,writing,research] [--sides with,without]

Outputs per run in <out_dir>/<task>-<side>/: the work, REPORT.md (the agent's final text),
result.json (cost, usage, duration), .sw-home/ for the "with" side.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

WITH_PREFIX = (
    "Use the stillwright skill and follow it. Skip onboarding questions: there is no user to "
    "ask; treat the task as an approved goal with no outward actions. Never push, publish or "
    "install anything. STILLWRIGHT_HOME is already set. When done, your final message is the "
    "notify card's text, as the skill says.\n\nTask: read TASK.md in the current folder and do it."
)
WITHOUT_PREFIX = (
    "Read TASK.md in the current folder and do it. Never push, publish or install anything. "
    "When done, write a short report for the user as your final message."
)
DISABLE_PLUGIN = json.dumps({"enabledPlugins": {"stillwright@stillwright": False}})


def run_one(fixture: pathlib.Path, out: pathlib.Path, side: str, model: str, extra=None, prompt=None) -> dict:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(fixture, out)
    env = {**os.environ, "STILLWRIGHT_HOME": str(out / ".sw-home")}
    repo = pathlib.Path(__file__).resolve().parents[2]
    env["PATH"] = os.pathsep.join([str(repo / "target" / "release"), os.path.expanduser("~/.cargo/bin"), env.get("PATH", "")])
    # Headless sessions must be told which tools they may use, or every Bash/fetch is denied.
    allowed = "Bash,Read,Edit,Write,Glob,Grep,WebFetch,WebSearch,Agent,Skill"
    text = prompt or (WITH_PREFIX if side == "with" else WITHOUT_PREFIX)
    cmd = ["claude", "-p", text,
           "--output-format", "json", "--model", model, "--permission-mode", "acceptEdits",
           "--allowedTools", allowed, "--settings", DISABLE_PLUGIN]
    if extra is not None:
        cmd += extra.split()
    elif side == "with":
        # Load the skills from the working tree, not the installed (published) plugin.
        cmd += ["--plugin-dir", str(pathlib.Path(__file__).resolve().parents[2])]
    proc = subprocess.run(cmd, cwd=out, env=env, capture_output=True, text=True, timeout=1800)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"is_error": True, "raw_stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    (out / "REPORT.md").write_text((data.get("result") or "") + "\n", encoding="utf-8")
    receipt = {k: data.get(k) for k in ("total_cost_usd", "duration_ms", "num_turns", "is_error")}
    receipt["usage"] = data.get("usage")
    receipt["modelUsage"] = {m: {k: v for k, v in u.items() if k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD")}
                             for m, u in (data.get("modelUsage") or {}).items()}
    if "raw_stdout" in data:
        receipt["raw_stdout"] = data["raw_stdout"]
        receipt["stderr"] = data["stderr"]
    (out / "result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixtures")
    ap.add_argument("out")
    ap.add_argument("--tasks", default="code,writing,research")
    ap.add_argument("--sides", default="with,without")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--with-extra", default=None, help="extra claude args for the 'with' side (replaces the default --plugin-dir)")
    ap.add_argument("--without-extra", default="", help="extra claude args for the 'without' side")
    ap.add_argument("--prompt", default=None, help="task prompt for both sides (replaces the built-in prefixes)")
    a = ap.parse_args()
    fixtures, out = pathlib.Path(a.fixtures), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for task in a.tasks.split(","):
        for side in a.sides.split(","):
            extra = a.with_extra if side == "with" else (a.without_extra or None)
            r = run_one(fixtures / task, out / f"{task}-{side}", side, a.model, extra=extra, prompt=a.prompt)
            cost = r.get("total_cost_usd")
            rows.append((task, side, cost, r.get("duration_ms"), r.get("num_turns"), r.get("is_error")))
            print(f"{task}-{side}: ${cost if cost is None else round(cost, 4)}  {r.get('duration_ms')} ms  turns={r.get('num_turns')}  error={r.get('is_error')}", flush=True)
    (out / "costs.json").write_text(json.dumps(rows, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
