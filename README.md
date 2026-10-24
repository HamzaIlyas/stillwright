# Stillwright

[![CI](https://github.com/HamzaIlyas/stillwright/actions/workflows/ci.yml/badge.svg)](https://github.com/HamzaIlyas/stillwright/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/HamzaIlyas/stillwright)](https://github.com/HamzaIlyas/stillwright/releases/latest)
[![License](https://img.shields.io/github/license/HamzaIlyas/stillwright)](LICENSE)

**A quiet maker for your AI agent.** It gets to know you, then keeps working on your goals:
plans them, finds and vets the right tools, proves every step, and only speaks when it
needs you, in five lines or fewer.

Any goal with a way to check it: code, research, writing, launches, operations. It runs
inside the agent you already use: Claude Code, Codex, Gemini CLI, OpenCode and any agent
that reads [Agent Skills](https://agentskills.io).

## Why

- **Agents say "done" when it isn't.** Stillwright passes a step only when an independent
  check proves it: tests run, page loads, source says so.
- **There are too many tools.** Thousands of skills, MCP servers and repos, some malicious.
  Stillwright picks by evidence, reads the code before trusting it, asks you once, and pins
  it by hash so it can't change silently. If nothing fits, it builds the tool itself.
- **Agents talk too much.** One inbox (ask, review, notify, idea). Silence is the default.

## Install

| Agent | Command |
|---|---|
| Claude Code | `claude plugin marketplace add HamzaIlyas/stillwright` then `claude plugin install stillwright@stillwright` |
| Codex | `codex plugin marketplace add HamzaIlyas/stillwright`, then install Stillwright from `/plugins` |
| Gemini CLI | `gemini extensions install https://github.com/HamzaIlyas/stillwright` |
| Cursor | loads the root `plugin.json` (Agent Plugins standard); marketplace listing pending |
| OpenCode, or any Agent Skills agent | `npx skills add HamzaIlyas/stillwright` |

The skills need the `sw` binary (a single file, no runtime). Any of these installs it:

```sh
# Linux / macOS
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/HamzaIlyas/stillwright/releases/latest/download/stillwright-installer.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -c "irm https://github.com/HamzaIlyas/stillwright/releases/latest/download/stillwright-installer.ps1 | iex"
# From source (needs Rust)
cargo install --git https://github.com/HamzaIlyas/stillwright --locked
```

On Linux and macOS the skills can also install it on first use (`scripts/get-sw.sh`, pinned
to a release version), when you are present to approve it.

## Use

New here? The [quickstart](docs/quickstart.md) takes ten minutes, and CI runs every command in it.

Tell your agent a goal, or just say **"stillwright"**. The first time, it asks a few short
questions to get to know you. After that:

```
sw status          what's going on, in three lines
sw inbox list      the only things that need you
sw goal add "..."  give it more work
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

All state is plain files in `~/.stillwright` (profile, goals, inbox, notes, pinned tools,
run logs). Nothing leaves your machine except what your agent already sends.

`sw` is a single Rust binary, so there is nothing to install besides it, and it is ready to
become a background service later.

## Status

v0.1. Each rule answers a failure that has been measured or reported, not a hunch:

- Agents mark work done without testing it: Anthropic's
  [notes on long-running agent harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).
  Hence independent, default-fail checks.
- Agents rarely ask for help at the right moment and fill gaps with wrong assumptions:
  [HiL-Bench](https://arxiv.org/abs/2604.09408). Hence the typed inbox with silence as default.
- Agent success falls as tasks get longer; METR measures how long a task an agent completes
  at 50% and at 80% reliability, and the 80% horizon is much shorter:
  [METR time horizons](https://metr.org/time-horizons/). Hence small, checkable steps.
- Hundreds of malicious skills were found on a public skill registry in early 2026 (341 of 2,857 scanned):
  [Snyk, "From SKILL.md to Shell Access"](https://snyk.io/articles/skill-md-shell-access/),
  [Unit 42 on the OpenClaw skill marketplace](https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain-risk/).
  Hence vetting, approval and hash-pinning before any third-party tool runs.
- In a controlled test with a limited verification budget, agents followed a constraint that
  had since been withdrawn in about three of four decisions:
  [arXiv 2608.25553](https://arxiv.org/abs/2608.25553). Hence dated notes that are retired, not overwritten.

Issues and PRs welcome. Found a gap? Open an [idea](https://github.com/HamzaIlyas/stillwright/issues/new?template=idea.yml).

MIT © Hamza Ilyas · Built at [Folvix](https://huggingface.co/Folvix).
