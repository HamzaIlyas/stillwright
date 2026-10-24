---
name: sw-verify
description: Independent proof that a step is really done. Runs the step's agreed check itself, and for anything a command can't prove, uses a fresh-context reviewer that can read but not edit and starts from "fail". Use after every Stillwright step, before telling the user anything is finished, and whenever someone asks "is it actually done/working?".
license: MIT
metadata:
  author: Hamza Ilyas
  version: "0.1.3"
---

# Verify

`sw` below is the Stillwright binary. If `sw` is not on PATH, follow the install note in the `stillwright` skill (ask the user first; never install unattended).

Agents regularly report work as done when it isn't: tests skipped, UI visibly broken, a
claim nobody checked. The worker's own report is evidence to check, never the verdict.

## Rules

- **Default is FAIL.** A step passes only with evidence that was opened and read.
- **The checker didn't decide the outcome.** Either a command fixed in the plan before the
  work started, whose real output you read and quote into the log (even if you also did the
  work, the command decides, not you), or a fresh subagent that never saw the worker's
  reasoning and has no edit tools.
- **The check was fixed before the work.** If the check changed afterwards, say so in the log.
- **Tests are read-only to the worker.** If a worker edited tests or check scripts to make
  them pass, that's a fail until a human agrees.

## Kinds of checks

| Work | Check |
|---|---|
| Code | the named tests, build and linters exit 0; for UI, load the page and look |
| Deploy / service | the URL returns the expected status and content; logs show no new errors |
| Files / config | the file exists and contains the required values (`grep`, parse it) |
| Writing | every requirement in the request ticked off; length and tone as asked |
| Research | each claim's source was fetched and actually says it; numbers have dates |
| Outward action | the result exists where it should (PR URL, published page, sent message id) |

## Fresh reviewer brief

When a command can't decide it, spawn a reviewer with: the request, the check, the paths
of the outputs, and "Start from FAIL. Pass only what you can prove from the files. List
each requirement as pass/fail with the evidence." Give it read-only tools.

## Result

Log it: `sw run log latest step=N result=pass|fail check="..." note="<evidence or error, one line>"`.
On fail, the note says exactly what broke so the retry can fix it.
