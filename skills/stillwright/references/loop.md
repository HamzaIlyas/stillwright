# The loop in full

The short form is in SKILL.md. This is the detail a long or unusual run needs.

## Planning
- `sw run new <slug> --goal "<text or id>" --plan <file|-> --freeze <paths>` opens the run,
  writes plan.md and freezes the files the checks depend on in one call. The older separate
  calls (`sw run new`, write plan.md, `sw run freeze`) still work.
- Plan format: `# Goal:` one sentence; one to three `Must not:` lines (the goal as stated is
  evidence of what the user wants, not the whole of it); numbered steps with `who:`, `outward:`,
  `check:` and `after:` fields; `Outward:` summary line. Pipes inside a check are kept, so put
  `check:` last before `after:`.
- `sw run brief` prints goal, must-nots and next step; the plugin runs it after every context
  compaction. Editing plan.md after work started is noticed once and dated in the log.
- The inbox refuses a fourth open question per run: ask early, ask right.
- In a git repository `sw run snapshot latest N` saves the tree before a step and `sw run
  rewind latest N` restores it; `sw run done` snapshots on its own. Outside git the receipt
  binds a hash of the folder's files instead; rewind is unavailable.

## Routing and cost
- `sw route <who>` names the cheapest model that passed four in five of at least three logged
  steps for that route; with no data, start small. The small model does every step a command
  can check. Keep mid for judgement no command checks, top only for a step mid failed.
- On a failed check, retry once one tier up with the error in the brief; a second failure
  stops what depends on the step.
- Log cost per step: `sw run log latest step=N who=<route> model=<model> in=<tokens>
  out=<tokens>`; `sw run cost` sums the run at the prices in `~/.stillwright/prices.json`;
  `sw run stats` shows pass rate and dollars per passed step per (who, model).
- One verification per step. A command that passes first time gets no retry; a code step with a
  test check gets its one review (see below) and nothing more.
- Cap what enters context; let subagents return answers, not transcripts; never switch the
  main conversation's model mid-run. A budget guard on the session (`codeburn guard install`,
  `docs/cost.md`) stops a runaway loop at a dollar amount.

## Proving a step
- `sw run check latest N` runs the `$` command, saves its output under `checks/`, writes a
  receipt (exit code, output hash, tree hash). `sw run done latest N` certifies: it refuses a
  failed receipt, a tampered frozen file, a receipt from another directory, a changed check
  command, a stale tree, and a code step without its review verdict. `sw run prove` is both.
- **Code steps.** The plugin's SessionStart hook records a baseline of the folder at session start (`sw run baseline` does it on other hosts: run it once when the session starts, before any edit; it refuses to overwrite a fresh one), so a file edited before `sw run new` still counts as changed. When code or test files changed since the run started (or since the last certified
  step), certification needs the reviewer's verdict in `checks/step-N-review.md`, logged with
  `sw run log latest step=N result=pass|fail evidence=<that file>` after the check it certifies;
  a later change means a new check and a new review. The check command's wording does not matter:
  the agent writes it. Logs, transcripts and host folders are neither hashed nor source. The verdict
  starts with PASS or FAIL, is logged after the check it certifies and on the same files, and a PASS
  names every changed file, tests included. The packet shows the changed files with their content
  when short and asks, per file, what it documents that the check did not exercise. A documented
  behaviour left broken or unimplemented is FAIL; an edge the file does not promise is a note.
- **Prose, research, design.** Same packet, same verdict; here the verdict is the pass and
  the log line carries `result=pass evidence=<file>`.
- The reviewer is a fresh read-only subagent on the small model that sees the packet and
  nothing else, never the run log or the worker's reasoning (`sw-verify`); the orchestrator saves
  its reply verbatim. sw checks the verdict's shape and binding, not who wrote it: the state
  folder is plain files, and the receipts are evidence for a reader, not a lock.

## Finishing and learning
- `sw run finish latest "<text>"` closes the goal and adds one notify card once every step
  passed; it refuses while a step is unproven. The final message is that text.
- Lessons: `sw lesson add "<one line>" --scope <goal word or global> --source self|reviewer
  --run <run>`; a lesson from a failure stays scoped; `sw lesson vote <id> up|down` when a later
  step used one; tool or web findings enter only with `--source tool|web` (quarantined).
- Preferences: `sw note add ... --source`; the user's own words in `profile.md` win.

## Talking to the user
- `ask`: blocked on a decision only they can make; one question with your recommended answer;
  three open per run.
- `review`: approve an outward action or a plan.
- `notify`: something finished or broke; never "still working".
- `idea`: a proposal they can accept (becomes a goal) or dismiss.
The user answers a card by telling you; record it with `sw inbox answer <id> "<answer>"`.
When the user is present, answer from `sw status` and the inbox in a few lines; never paste logs.

## Budgets and drift
Each run: 30 subagent calls or 2 hours, whichever first; at the limit stop, write where things
stand in the log, one notify card. The same action failing three times in a row, or a claim
that contradicts tool output, is drift: stop and ask.
