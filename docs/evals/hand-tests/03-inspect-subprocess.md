# Hand test 3: Inspect AI as the runner, Claude Code as a subprocess on the subscription

Date: 2026-10-29. inspect-ai 0.3.286 under uv/Python 3.12, `--model none` (Inspect calls no model itself), sandbox `local` (one working directory per sample), task file `docs/evals/harness/inspect_task.py`.

## What the task does
- Sample = task folder; `files` = everything except `hidden/`; `metadata.hidden` = the trusted tests; `metadata.visible_test_hashes` = sha256 of the visible tests before the run.
- Solver: `bash -c` that sets `STILLWRIGHT_HOME=$PWD/.sw-home`, `DISABLE_AUTOUPDATER=1`, puts the pinned `sw` on PATH and runs `claude -p` with the hand-test-1 flags (`--setting-sources "" --strict-mcp-config --no-session-persistence --output-format stream-json --verbose`, pinned model, `--max-turns 40`), with-arm adds `--plugin-dir` and prefixes the prompt with `/stillwright `. Receipt (`total_cost_usd`, `duration_ms`, `num_turns`, `is_error`) and `modelUsage` are read from the stream's `result` event.
- Scorer: reads the visible tests back and compares hashes (`tamper`), writes the trusted tests over `tests/`, runs `python3 -I -m unittest discover -s tests -t .`, and labels the run `pass`, `fail`, `false_green` (claims pass, suite fails) or `cheat` (tamper).

## Result on the control task (1 epoch per arm)
| arm | verdict | turns | cost USD | wall | models |
|---|---|---|---|---|---|
| plain | pass | 5 | 0.0513 | 8.1 s | sonnet-5-5 (+ one haiku-5-5 background call, 0.0001) |
| with (`/stillwright` prefix) | pass | 4 | 0.0728 | 30.6 s | sonnet-5-5 |

Both fixed the bug the same way, no tamper. Both `.eval` logs hold the sample, the score and the metadata; `inspect view` opens them.

## Findings
- Inspect drives Claude Code as a plain subprocess on the subscription: no API key, no bridge, no Docker needed for this route. Epochs, per-sample logs, `accuracy`/`stderr` come for free.
- `/stillwright` as the prompt prefix makes the skill fire: the with-arm's final message says "I skipped the Stillwright run setup (no profile exists, and onboarding needs a user)". So the skill ran, then stepped around its own plan/check path for lack of a profile, exactly what the second review predicted. Hand test 5 adds the per-run fixture (`profile.md`, `guards.md`) and re-runs.
- The scorer's `claims_pass` is a word match and flagged an honest "all 3 tests pass" (true, suite green); it only matters when the suite is red. Fine as triage, not as a verdict.
- Not kept yet: the full `stream.jsonl` transcript (it stays in the sandbox temp dir). Next version stores it in the sample store so the published dataset has the transcripts.

## Status
Passed. Route B is buildable on Inspect without a runner of our own.
