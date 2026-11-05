# Hand test 7: the Stop hook under headless Claude Code

Date: 2026-11-05. Branch `feat/plugin-hooks-stop`, commit 8173258. Claude Code headless, model `claude-haiku-5-5`, flags `--setting-sources "" --strict-mcp-config --permission-mode acceptEdits --allowedTools Bash --plugin-dir <this repo> --max-turns 8 --no-session-persistence`, fresh `STILLWRIGHT_HOME` and a fresh git folder per probe, `sw` from `target/release` on PATH. No `sw init`: the only hooks are the plugin's `hooks/hooks.json`.

## Probe 1: a step the model can prove

Plan: `1. append the word probe to a.txt | check: $ grep -q probe a.txt`. Prompt: "Append the word probe to a.txt with one shell command, then reply with the single word done."

What happened, from the stream:
1. SessionStart hook ran: the brief was injected (`Stillwright run … (0/1 steps passed) … Next: step 1 …`).
2. The model ran `echo probe >> a.txt` and replied `done`.
3. The Stop hook blocked: the model received the reason verbatim (`stillwright: run … step 1 (append the word probe to a.txt) has no receipt, so this turn cannot end as done. Run \`sw run check … 1\` and then \`sw run done … 1\` …`).
4. The model ran `sw run check` (passed), then `sw run done`, which was refused as a stale receipt (the tree changed between the two commands), then `sw run check … && sw run done …` in one command: certified.
5. The model's final message said the step is done and certified and explained the refusal. The next stop was allowed: 1/1 steps passed. 6 turns, 0.0050 USD.

## Probe 2: a step the model cannot prove (the once-only path)

Plan: `1. make the suite pass | check: $ false`. Prompt: "Reply with the single word done. Do not run any commands unless something tells you that you must."

1. The model replied `done`.
2. The Stop hook blocked with the same shape of reason.
3. The model ran `sw run check … 1` (exit 1), then `sw run log … step=1 result=fail note="check failed (exit 1): the step 1 check command exits 1, so the suite does not pass yet; I have not changed any code"`.
4. Its final message: "I'm not able to mark this done. The step 1 check failed, so the suite does not pass yet." The next stop was allowed on two grounds at once: the step was logged as failed, and `stop_hook_active` was true (the host was continuing because of the hook). 4 turns, 0.0042 USD.

## Observations
- Both plugin hooks (SessionStart, Stop) loaded under `--setting-sources ""` with no settings file at all, confirming the earlier probe for PreToolUse.
- The host's stream shows a `notification` with key `stop-hook-error` ("Stop hook error occurred") at the moment of the block, with no `hook_started`/`hook_response` records for Stop (unlike SessionStart). The reason reached the model intact, so this is how the host reports a stop-hook block in `stream-json`, not a failure of the hook. Noted as a limit: a user watching the terminal sees the word "error".
- The stale-receipt refusal in probe 1 is the certificate mechanism working: something in the working tree changed between the check and the done (the tree hash includes untracked files), so the model had to check again on the tree as it is now.
- `sw run stop` (plain mode) before probe 1 printed the block reason; after both probes it printed `allow`.

Unit coverage of the paths the probes did not reach (card waiting, other folder, prose steps, malformed event): `StopHookTests` in `tests/test_sw.py`.
