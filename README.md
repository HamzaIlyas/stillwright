# Stillwright

**A quiet maker for your coding agent.** It learns you once, then keeps working: it plans
your goals, finds and vets the right tools, proves every step, and only speaks when it
needs you, in five lines or fewer.

Works with Claude Code, Codex, Gemini CLI, OpenCode and any agent that reads
[Agent Skills](https://agentskills.io).

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
| Codex | `codex plugin marketplace add HamzaIlyas/stillwright` |
| Gemini CLI | `gemini extensions install https://github.com/HamzaIlyas/stillwright` |
| Any Agent Skills agent | `npx skills add HamzaIlyas/stillwright` |

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

`sw` is written in Rust: one small binary per platform, instant start, and a compiler that
rejects whole classes of bugs before anything runs, which matters for a tool that will later
run as a background service and extend itself.

## Status

v0.1. The rules are built on published research about where agents fail (self-judged
"done", interrupting too much, malicious skills, runaway costs). Issues and PRs welcome.

MIT © Hamza Ilyas · Built at Folvix.
