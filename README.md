# Stillwright

[![CI](https://github.com/HamzaIlyas/stillwright/actions/workflows/ci.yml/badge.svg)](https://github.com/HamzaIlyas/stillwright/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/HamzaIlyas/stillwright)](https://github.com/HamzaIlyas/stillwright/releases/latest)
[![License](https://img.shields.io/github/license/HamzaIlyas/stillwright)](LICENSE)

**Your agent says "tests pass". Stillwright makes it prove it.** A step is done only when
its check ran and passed on the files as they are right now, with a receipt in the log, and
any step can be undone. For Claude Code, Codex, Gemini CLI, Cursor, OpenCode and any agent
that reads [Agent Skills](https://agentskills.io).

![sw status, a run two steps in, one review card answered, two goals](assets/demo.gif)

## See it work

A plan step with a command as its check. The agent cannot write "pass" by hand; it has to
run the check, and the receipt records what ran, the exit code and a hash of the working
tree:

```
$ sw run freeze latest tests
frozen: tests; any change fails the step's check until frozen again

$ sw run log latest step=1 result=pass
step 1 has a command check; a pass written by hand is not evidence.
Run `sw run check latest 1`, then `sw run done latest 1`.

$ sw run check latest 1
step 1: check failed (exit 1); output in ~/.stillwright/runs/20261029-031220-discount-floor/checks/1-2026-10-29031220.log

(the agent fixes pricing.py)

$ sw run check latest 1
step 1: check passed (exit 0, 0.1s, tree 64c2003852c2); `sw run done` when the step's work is complete

$ sw run done latest 1
step 1: done, certified (`python3 -m unittest -q tests.test_pricing` exit 0 on tree 64c2003852c2)

(something goes wrong later)

$ sw run rewind latest 1
step 1: files restored from snapshot 8bcbaf39015a (0 newer files removed);
the state before is kept at refs/sw/20261029-031220-discount-floor/before-rewind-2026-10-29031220
```

Real output from v0.2, unedited except for the home folder. If the agent edits a test after
`sw run freeze`, the check fails as tampered. If files change after the check, `sw run done`
refuses the stale receipt. The rewind keeps the state it replaced, so nothing is lost.

## What it does

- **Proof, not claims.** Every step of a plan has a check written before the work. A command
  check is run by `sw`, with a receipt; anything else is judged by a fresh reviewer that never
  saw the worker's reasoning.
- **Undo.** Every certified step leaves a git snapshot (untracked files included) under
  `refs/sw/`; `sw run rewind` brings it back.
- **Vetted tools.** Thousands of skills and MCP servers, some malicious. Stillwright picks by
  evidence, reads the code before trusting it, asks you once, and pins it by hash so it cannot
  change silently.
- **Quiet.** One inbox with four card types (ask, review, notify, idea). Silence is the default,
  and the agent's final message is at most five lines.
- **Goals, not prompts.** It keeps a goal queue, plans each goal into checkable steps, routes
  steps to the cheapest model that a command can verify, and measures the dollars.

## Measured

Three small tasks (code, writing, research), each done by a fresh Claude Sonnet agent with and
without the Stillwright skills, graded by scripts and a read-only judge. Both sides finished
every task. The plain side made one false claim; Stillwright made none and left a plan and a
log every time. It cost about the same in dollars and more wall time. Three tasks is a small
sample and is stated as such; raw runs, grading script and judge report:
[docs/evals.md](docs/evals.md) and the
[Hugging Face dataset](https://huggingface.co/datasets/Folvix/stillwright-evals).

The gate itself is tested: 67 black-box tests drive the binary on Linux, macOS and Windows in
CI, including the ways two independent reviews found to get past it before release.

## Install

One line for most agents:

```sh
npx plugins add HamzaIlyas/stillwright   # as a plugin: Claude Code, Cursor, Codex, Copilot CLI, VS Code, Grok Build, Kimi Code
npx skills add HamzaIlyas/stillwright    # as skills: 75+ agents, including all of the above
```

Or the agent's own way:

| Agent | Command |
|---|---|
| Claude Code | `claude plugin marketplace add HamzaIlyas/stillwright` then `claude plugin install stillwright@stillwright` |
| Codex | `codex plugin marketplace add HamzaIlyas/stillwright`, then install Stillwright from `/plugins` |
| Gemini CLI | `gemini extensions install https://github.com/HamzaIlyas/stillwright` |
| Cursor | loads the root `plugin.json` (Agent Plugins standard); marketplace listing pending |
| OpenCode, or any Agent Skills agent | `npx skills add HamzaIlyas/stillwright` |
| Hermes Agent | `git clone --depth 1 https://github.com/HamzaIlyas/stillwright /tmp/stillwright && mkdir -p ~/.hermes/skills/stillwright && cp -R /tmp/stillwright/skills/. ~/.hermes/skills/stillwright/` |

For a whole team: run `sw init` in the repository and commit the two files it writes
(`.claude/settings.json`, `.github/copilot/settings.json`).

The skills need the `sw` binary (a single file, no runtime). Any of these installs it:

```sh
pip install stillwright                                   # any OS with Python
brew install HamzaIlyas/tap/stillwright                   # macOS / Linux with Homebrew
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/HamzaIlyas/stillwright/releases/latest/download/stillwright-installer.sh | sh   # Linux / macOS
powershell -ExecutionPolicy Bypass -c "irm https://github.com/HamzaIlyas/stillwright/releases/latest/download/stillwright-installer.ps1 | iex"   # Windows
cargo install --git https://github.com/HamzaIlyas/stillwright --locked   # from source
```

## Use

New here? The [quickstart](docs/quickstart.md) takes ten minutes, and CI runs every command in it.
Also: [troubleshooting](docs/troubleshooting.md), [Windows notes](docs/windows.md),
[coming from OpenClaw or Hermes](docs/migrate.md), a [real example run](examples/quickstart-run/README.md),
and a [press kit](press/README.md).

Tell your agent a goal, or just say **"stillwright"**. The first time, it asks a few short
questions to get to know you. After that:

```
sw status          what's going on, in a few lines
sw inbox list      the only things that need you
sw goal add "..."  give it more work
sw run status      the current plan, step by step, with what is proven
sw run cost        dollars a run spent, by model
```

To keep it working while you're away, schedule one loop per hour, for example
`claude -p "Use the stillwright skill: run one loop, then stop."` from cron. Unattended runs
never push, deploy, publish or install anything new; those wait in your inbox.

## What's inside

| Skill | Does |
|---|---|
| `stillwright` | the loop: pick goal → plan → get tools → execute → verify → report |
| `sw-onboard` | learns who you are and what you want, in three short rounds at most |
| `sw-scout` | finds, vets, trials and pins the best existing tool for a job |
| `sw-forge` | builds and tests a new skill when nothing good exists |
| `sw-verify` | independent, default-fail proof for every step |
| `sw-radar` | spots what matters to you (updates, risks, new tools) as rare idea cards |
| `sw-deep-search` | research that ends in verified, sourced answers |
| `sw-context-diet` | keeps long sessions lean and cheap |
| `sw-launch` | pitch, README, posts and launch plan for what you build |

All state is plain files in `~/.stillwright` (profile, goals, inbox, notes, pinned tools, run
logs, receipts). Nothing leaves your machine except what your agent already sends. `sw` is a
single Rust binary.

## Why these rules

Each one answers a failure that was measured or reported, not a hunch:

- Agents mark work done without testing it, and judges that read the agent's prose cannot
  tell: Anthropic's [notes on long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents);
  [arXiv 2607.14890](https://arxiv.org/abs/2607.14890) (evidence-gated loops cut hidden
  failures from 31 to 2 per 1,800). Hence receipts, and a reviewer that is a gate.
- Agents weaken tests to make them pass and pipe test output so failures exit 0
  ([anthropics/claude-code #319](https://github.com/anthropics/claude-code/issues/319)). Hence
  frozen check files and `pipefail`.
- Undo of agent edits is the most-requested feature no host ships
  ([openai/codex #9203](https://github.com/openai/codex/issues/9203)). Hence snapshots and rewind.
- Agents rarely ask at the right moment and fill gaps with wrong assumptions:
  [HiL-Bench](https://arxiv.org/abs/2604.09408). Hence the typed inbox, silence by default.
- Hundreds of malicious skills were found on a public registry in early 2026 (341 of 2,857):
  [Snyk](https://snyk.io/articles/skill-md-shell-access/),
  [Unit 42](https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain-risk/). Hence vetting,
  approval and hash-pinning before any third-party tool runs.
- Agent success falls as tasks get longer: [METR time horizons](https://metr.org/time-horizons/).
  Hence small, checkable steps.

Cost is measured, not assumed: the harness, the price table and the cache linter are in
[docs/cost.md](docs/cost.md). Known limits are listed in the [CHANGELOG](CHANGELOG.md).

## Who runs it

One person, [Hamza Ilyas](https://github.com/HamzaIlyas), building it at
[Folvix](https://huggingface.co/Folvix). Questions and ideas:
[Discussions](https://github.com/HamzaIlyas/stillwright/discussions). Bugs:
[issues](https://github.com/HamzaIlyas/stillwright/issues/new?template=idea.yml), read daily.

MIT.
