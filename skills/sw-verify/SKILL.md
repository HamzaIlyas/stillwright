---
name: sw-verify
description: Independent proof that a step is really done. Runs the step's agreed check itself, and for anything a command can't prove, uses a fresh-context reviewer that can read but not edit and starts from "fail". Use after every Stillwright step, before telling the user anything is finished, and whenever someone asks "is it actually done/working?".
license: MIT
metadata:
  author: Hamza Ilyas
  version: "0.1.5"
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

## When a reviewer is needed at all

A command that exits 0 is the cheapest and most honest verdict there is. Use a model reviewer
only for work no command can judge (prose, research, design), and run it on the small model
in a fresh context: it reads the output and the check, nothing else, so it costs cents.

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

When a command can't decide it, run `sw run review latest N` and give the reviewer that
packet and nothing else: it holds the goal, the must-nots, the step and its check, the diff
since the last snapshot (new files included) and the latest check output, and it leaves out
what the worker said. The packet ends with the brief ("Start from FAIL. Pass only what the
changes and the output prove; list each requirement of the check as pass or fail with the
evidence") and
the path the verdict goes to (`<run>/checks/step-N-review.md`). Give the reviewer read-only
tools; it may open files the packet names, never the run log.

## Result

Log it: `sw run log latest step=N result=pass|fail check="..." evidence=<verdict file> note="<one line>"`.
A pass on a step with no command check is refused without `evidence=`: a non-empty file
(the verdict, a screenshot, the fetched page), stored with its hash, so the claim and what
backed it can be opened together later. On fail, the note says exactly what broke so the
retry can fix it.
