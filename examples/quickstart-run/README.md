# Example: a real run

This is the actual `~/.stillwright` state from the run that produced
[docs/quickstart.md](../../docs/quickstart.md), copied unchanged. Read it top to bottom to see
what Stillwright leaves behind:

- `profile.md`: what the user said (short, in their words).
- `goals.json`: the goal, with when it was opened and closed.
- `runs/<id>/plan.md`: one line per step, each with its check decided up front.
- `runs/<id>/log.jsonl`: the one-way log. Note step 1 **failed first**: the doc check caught a
  command-splitting bug and a command that could not work in a fresh home. The fix was made
  and the check rerun before the step was marked passed. That is the loop working.
- `inbox.json`: the single `notify` card the user saw. Nothing else was said.

Reproduce the checks yourself from the repo root, after `cargo build --release`:

```sh
python3 scripts/check_docs.py docs/quickstart.md
```
