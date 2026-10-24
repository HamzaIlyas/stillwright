# Evals

Measured, not claimed. Three small real tasks, each done twice by a fresh agent of the same
model (Claude Sonnet): once told to follow the Stillwright skills, once with no skill at all.
Everything below can be re-checked from [`docs/evals/2026-10-24/`](evals/2026-10-24/): the
tasks, every agent's work and report, the Stillwright plans and logs, and the grading script.

## Tasks

| Task | What had to happen |
|---|---|
| code | Make 5 unit tests pass in a tiny pricing module (one real bug: a discount could go negative) without touching the tests |
| writing | Rewrite a marketing paragraph into plain English, at most 80 words, keeping four facts exactly, no marketing adjectives |
| research | Find the latest version of this project on PyPI and on GitHub, say whether they match, give the GitHub release date, cite the URL for every fact |

## What was graded

- **done**: a script checks the result (tests pass with tests unchanged; word count and facts; correct version, date and URLs).
- **evidence**: the report to the user quotes the proof (test output, word count, URLs). Script-checked.
- **5 lines or fewer**: the report to the user is at most five non-empty lines, as the skill asks. Script-counted.
- **plan + log**: a plan with the check for each step written before the work, and a pass/fail log. Script-checked.
- **false claims**: a separate read-only judge listed every factual claim in each report and checked it against the files and the cited URLs.

## Results (2026-10-24)

| Task | Side | done | evidence | 5 lines or fewer | plan + log | false claims | wall time | tokens |
|---|---|---|---|---|---|---|---|---|
| code | Stillwright | yes | yes | no (8) | yes | 0 | 107 s | 78k |
| code | plain | yes | yes | no (7) | no | 0 | 64 s | 71k |
| writing | Stillwright | yes | yes | no (8) | yes | 0 | 156 s | 86k |
| writing | plain | yes | yes | no (8) | no | 1 | 74 s | 71k |
| research | Stillwright | yes | yes | no (22) | yes | 0 | 147 s | 87k |
| research | plain | yes | yes | no (26) | no | 0 | 88 s | 73k |

Wall time and tokens are the whole run, as reported by the harness; each run folder has a `timing.json` with them.

## What this says

- **On tasks this small, a plain agent does the work just as well.** All six runs finished
  the task correctly with evidence. Stillwright's value did not show up in "done".
- **Stillwright leaves a record a human can audit.** All three runs wrote a plan whose
  checks were fixed before the work, and a log with the check output. None of the plain
  runs left anything.
- **Stillwright caught its own mistake once.** In the writing task, its first draft added
  two things the user had not asked for. The fresh reviewer the skill requires failed that
  draft, the agent removed them, and the log shows fail → fix → pass. The plain run kept an
  unrequested sentence and said the facts were "kept exactly" although it had changed the
  wording, which it disclosed two lines later: the one false claim found, a mild one.
- **Stillwright broke its own five-line rule every time.** Reports were 8, 8 and 22 lines
  (the plain side's were 7, 8 and 26, but it had no such rule). The one-line inbox cards
  were short; the report it returned was not. This is a
  real gap between the skill text and behaviour, and the next skill change targets it.
- **It costs more**: roughly 1.7–2x the wall time and 10–20% more tokens, spent on the
  plan, the checks and the reviewer.

## Re-run after the skill change (same day)

The five-line failure led to one change: the skill now says the final message *is* the
notify card's text, and two helper skills (deep-search, scout) were told to keep their
reports inside that limit. The three Stillwright runs were repeated with the changed skill
(the plain side was not re-run; nothing changed for it). Raw runs: [`rerun-1/`](evals/2026-10-24/rerun-1/).

| Task | done | evidence | 5 lines or fewer | plan + log | wall time | tokens |
|---|---|---|---|---|---|---|
| code | yes | yes | yes (4) | yes | 33 s | 76k |
| writing | yes | yes | yes (3) | yes | 40 s | 77k |
| research | yes | yes | yes (4) | yes | 53 s | 79k |

All three now meet the rule, with the proof still in the message (test output, word count
and fact check, URLs). Wall time also dropped to about half of the plain runs' first-round
times; one re-run is not enough to say that is real rather than variance. The "false claims"
column was not re-judged for this round.

## Limits of this eval

- Three tasks, one run each per side. Enough to see patterns, not to put error bars on them.
- Both sides used the same model; a stronger or weaker model may shift all columns.
- The tasks are single-sitting and small. Stillwright's design targets long, multi-step
  work with outward actions and unattended runs; none of that is exercised here.
- Onboarding was skipped (no user to ask), so the profile and notes parts of the skill
  were not tested.
- The grading script and the judge prompt were written by the skill's author. The judge is
  a model, and its full report is in [`judge-false-claims.md`](evals/2026-10-24/judge-false-claims.md) for anyone to dispute.
- One harness quirk: the plain research agent was refused permission to write its report
  file, so for fairness every agent's returned text was saved as its report by the eval
  runner, identically for all six.

## Reproduce

```sh
cd docs/evals/2026-10-24
python3 grade.py runs      # first round, both sides
python3 grade.py rerun-1   # Stillwright side after the skill change
```

The script re-runs the tests, recounts the words, rechecks the facts and the logs. Only the
"false claims" column needs a reader (or a fresh model) going claim by claim.
