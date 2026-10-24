---
name: sw-context-diet
description: Keeps the agent's context window lean so long work stays sharp and cheap. Moves bulky reading into subagents, saves state to files before compaction, trims loaded skills/tools/memory, and summarizes instead of pasting. Use when a session gets long or slow, before a big multi-file task, when the agent starts forgetting earlier decisions, when tool output is huge, or when the user mentions tokens, cost, context, or "it's getting confused".
license: MIT
metadata:
  author: Hamza Ilyas
  version: "0.1.3"
---

# Context diet

`sw` below is the Stillwright binary. If `sw` is not on PATH, follow the install note in the `stillwright` skill (ask the user first; never install unattended).

Quality drops and cost rises as context fills: early decisions get lost and huge outputs
crowd out the task. Treat context as the scarcest resource in the run.

## While working

- **Delegate reading.** Wide searches, long files and logs go to a subagent that returns
  only the answer (paths, line numbers, the one relevant excerpt).
- **Read narrow.** Search first, then read only the lines needed. Don't reread files you
  just wrote.
- **Cap tool output.** Pipe through `head`, `tail`, `grep`, or `--quiet` flags. Summarize
  results in one line instead of carrying them forward.
- **Decide once.** Write decisions into the run's `plan.md` or log so they survive compaction.

## Before context runs out (around 80% full)

1. Save state: `sw run log latest event=checkpoint note="<where we are, next step>"` and update `plan.md`.
2. Compact or start a fresh session; resume with `sw run status`.

## Trim what's loaded

Every installed skill, tool and MCP server adds its description to every session. Review
what's loaded: keep the ones used weekly, uninstall or disable the rest (they stay findable
through `sw-scout`). Keep memory indexes to one line per entry, details in separate files.

## Report

When asked, say in one line where context is going (largest consumers) and what was trimmed.
