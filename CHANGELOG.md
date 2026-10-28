# Changelog

## Unreleased
- Consequence gate: `sw gate <command>` judges a shell command before it runs and exits allow (0), ask (3) or block (2), printing the resolved paths and the blast radius (files under a folder to be removed, uncommitted changes a `git reset --hard` would discard). Built in: recursive deletes (ask inside the workspace, block outside it or on a root folder or the home folder), `git push --force`, `reset --hard`, `clean -f`, `checkout --`/`restore`, `branch -D`, `stash drop`, history rewrites, downloads piped into a shell, `DROP`/`TRUNCATE`/unfiltered `DELETE`, `terraform destroy`, `kubectl delete`, `docker system prune`, `dd` onto a device, reformatting. Wrappers with their options (`sudo -u root`, `env -i`, `nice -n 5`, `timeout 5`, `bash -lc`, `eval`, `xargs rm`), absolute paths, subshells, `$(…)`, loop and `if` bodies, and `cd … && …` (judged where it lands) do not hide the command; `git -C`/`-c` options, `-fu` flag clusters, `+ref`/`:ref` refspecs, `--mirror` and plain `git restore <file>` are caught; `find -delete`, `rsync --delete`, `truncate`, `mv … /dev/null`, inline `python -c` deletes and `mkfs.*` are covered. The workspace is the repository the command runs in (not the current folder), a missing target does not ask, deleting the workspace itself blocks, and `git branch -d` or `diskutil list` do not ask. A fresh adversarial review drove the list; what it still cannot see (a script file, an encoded payload, a glob the shell expands) is why it sits in front of the host's sandbox, not instead of it. `guards.md` in the state folder or in `.stillwright/` of the repository adds the user's own `never:` and `ask:` lines. `sw gate --hook` speaks Claude Code's PreToolUse JSON, and `sw init` wires it into `.claude/settings.json` together with a SessionStart hook. Text matching is not a security boundary; it is the cheap layer in front of the host's sandbox.
- Constraints that survive compaction: `sw run brief` prints the goal, `Must not:` lines, outward line and next step of the newest open run that was started in this folder (or a parent or child of it), lines clipped, so a run from another project never leaks into a session; `sw run new` records where it was started. Wired by `sw init` as a SessionStart hook for `startup|resume|compact`, so a compacted session gets them back.
- `sw run next` lists the steps whose `after:` dependencies passed, so independent steps can run in parallel.
- `sw run stats` and `sw route <who>`: one row per step across all runs (a certified `done`, its cost lines and its retries count once), with the route from the plan's `who:` when the log has none; pass rate and dollars per passed step per (who, model); `sw route` names the cheapest model with at least three steps, four passes in five and token counts logged, or says there is not enough data.
- Question budget: at most three open ask cards per run; the fourth is refused with the reason.
- `sw lesson add|list|vote|trust|for`: lessons with provenance (source, run), scope (`global` or a goal word), helpful/harmful votes, a 90-day expiry renewed by a vote up, and quarantine for lessons from tool or web output until `sw lesson trust`. `sw lesson for "<goal>"` returns at most five, best first; they are suggestions, never rules. Sources are validated (`self`, `reviewer`, `user`, `tool`, `web`), `trust` keeps the provenance (`web, trusted`), and the question budget counts a run under any spelling of its name.
- Certificates: a step whose check is `check: $ <command>` is proven, not claimed. `sw run check` runs the command (bash with pipefail, so a failure inside a pipe fails) and writes a receipt: command, exit code, output hash, output file under `checks/`, hash of the working tree as git would commit it (untracked files included). `sw run done` passes the step only with a passing receipt taken on the working tree as it is now; `sw run log … result=pass` is refused for such steps. `sw run freeze <paths>` records the hashes of test and script files; any later change fails the check as tampered until they are frozen again, and both freezes stay in the log. The stillwright skill now writes checks as commands.
- Hardening from a fresh-context review that reproduced three bypasses: `sw run log` refuses duplicate keys (`result=fail result=pass` used to slip through); `sw run done` refuses a receipt whose command differs from what plan.md now says, and checks frozen files too; git failing inside a repository is an error, never a silent "none" tree; frozen paths are stored absolute so the directory you run from does not matter; hashing uses a temp object store, so `sw run check` writes nothing into `.git/objects`; the state folder is excluded from the tree hash when it lives inside the repository; `$` is a command only with a space after it (`$5 refund shown` stays prose). Known limits: ignored files and nested repositories are not part of the tree hash; no timeout on a check; no pipefail on Windows.
- Second review round: a rewind never removes the state folder when it lives inside the repository; two rewinds in one second keep both saved states (a snapshot never overwrites a ref); a frozen symlink is frozen as the link, so retargeting it is tampering; file names git would quote are removed correctly on rewind, and emptied directories go with them; the receipt records the directory the check ran in and `sw run done` must run from the same one; snapshots carry their own git identity, so a machine without `user.name` still works; outside git, `sw run done` warns that the receipt is not tied to the files.
- Rewind: every `sw run done` in a git repository saves a snapshot of the working tree (untracked files included, ignored files left out) as a commit under `refs/sw/<run>/step-N`, without touching the branch, index or HEAD; `sw run snapshot <run> <step>` saves one before a step starts. `sw run rewind <run> <step>` restores the files of that snapshot, removes files added since (never ignored ones), and first saves the state it replaces under `refs/sw/<run>/before-rewind-<time>`, so a rewind can be undone.

## 0.1.5 - 2026-10-26
- `sw run cost` (dollars per run from logged tokens at `prices.json` rates) and `sw cache` (names the turns that broke the prompt cache in a Claude Code transcript).
- Cost rules in the stillwright skill, `sw-worker` forked small-model skill, docs/cost.md, docs/prices.example.json, and the A/B cost harness docs/evals/run_eval.py; priced eval round in docs/evals.md (no saving on small tasks, stated as such).
- sw-scout vetted list: codeburn, ccusage, rtk; routers that proxy keys listed under avoid.

## 0.1.4 - 2026-10-26
- `sw status` shows the top open goal and the ask/review cards that need the user.
- Evals published as a Hugging Face dataset (Folvix/stillwright-evals); judge report and per-run timing committed.
- Homebrew: `brew install HamzaIlyas/tap/stillwright` (formula published to HamzaIlyas/homebrew-tap on each release).
- sw-forge: forge only on logged triggers, evidence file required, old-vs-new eval before install, rollback copy, usage tracking and a retire card (design from SkillsBench, Hermes, Prime Agent, ECC, skill-creator).

## 0.1.3 - 2026-10-24
- press/ kit (logo, social card, horizontal and vertical demo clips, pitch, prompts) and docs/migrate.md (from OpenClaw or Hermes).
- `sw init`: writes the repo-level settings that turn Stillwright on by default in Claude Code and GitHub Copilot.
- README: `npx plugins add` / `npx skills add` one-liners; `.agents/skills` mirror; GitHub topics for the Gemini gallery.

## 0.1.2 - 2026-10-24
- docs/evals.md: re-run after the skill change; all three runs within five lines.
- sw-scout: references/vetted-tools.md, a checked starter list with an avoid list.
- stillwright skill: the final message is the notify card text; five-line rule applies to it (gap found by the eval).
- docs/evals.md: first measured comparison against a plain agent, with raw runs and grading script.
- `pip install stillwright` (published to PyPI from 0.1.1).
- Hermes Agent install row (drop-in to ~/.hermes/skills/).

## 0.1.1 - 2026-10-24
- README: badges, cited research behind each rule, Folvix link; issue and PR templates.
- Codex-native marketplace file (.agents/plugins/marketplace.json); install table covers Cursor and OpenCode.
- docs/quickstart.md, verified by scripts/check_docs.py in CI; examples/quickstart-run with the real run state.
- docs/troubleshooting.md and docs/windows.md.
- Demo GIF in README; `pip install stillwright` packaging (maturin) with a PyPI Trusted Publishing workflow.

## 0.1.0 - 2026-10-23
- First release: the `stillwright` loop and eight `sw-*` skills.
- `sw` state keeper in Rust: goals, runs, inbox, notes with validity, hash-pinned tools.
- Packaging for Claude Code, Codex, Gemini CLI and Agent Skills agents.
