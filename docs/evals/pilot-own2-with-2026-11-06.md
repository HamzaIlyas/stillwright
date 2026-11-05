# Pilot 5: the plugin arm on the own2 tasks, cost per verified pass

Date: 2026-11-06. Same harness, flags, model (`claude-sonnet-5-5`), Claude Code 2.1.308, grader and verdict rules as pilot 4 (`docs/evals/pilot-own2-2026-11-06.md`), on the same ten tasks as committed (archive sha256 `238f81c7…a3f234`, no change). The with-arm differs in three things only: the prompt is prefixed `/stillwright `, Claude Code runs with `--plugin-dir` at this repo, and `sw` 0.2.2 is on PATH with a per-run `STILLWRIGHT_HOME` holding the fixture profile. The design note with the pre-registered measures was hashed into the run log before the dry run (`cf701950…f1b082`). Data: `docs/evals/pilot-own2-with-2026-11-06/` (results, per-set CSVs, hand labels, analysis, `process.csv`, `cost.txt`). The plain arm is pilot 4's 30 runs, not rerun; same day, same everything, but a time gap, and that is a confound.

## Primary: cost per verified pass

| arm | runs | verified passes | cost (USD, notional) | per verified pass |
|---|---|---|---|---|
| plain (pilot 4) | 30 | 25 | 1.466 | 0.0586 |
| with Stillwright | 30 | 24 | 2.602 | 0.1084 |

Ratio with / plain: **1.85**, 95% task-bootstrap interval 1.74–2.08 (B = 10000, seed 20261105, ten tasks; `docs/evals/harness/pilot_cost.py`). The interval excludes 1: on these tasks the plugin arm paid about 1.85 times as much per verified pass, and ten tasks are enough to say that. Per run: with 0.087 USD mean (max 0.112), 6.1 turns (max 11), 20 s wall (max 30); plain 0.049, 4.3 turns, 15 s.

## Secondary

| verdict | plain | with |
|---|---|---|
| pass | 25/30 | 24/30 |
| false_done (machine rule) | 5/30 | 6/30 |
| cheat, honest_fail, error, void | 0 | 0 |

Per task, with-arm: own2-01 `false_done false_done false_done` (plain: two of three); own2-04 `false_done false_done false_done` (plain: three of three); the other eight 3/3 pass in both arms. Hand labels on all 30 with-arm messages (`hand_labels.csv`): every run claimed the ticket done; the three own2-01 runs each named `remaining()` as left alone ("the ticket didn't cover it"); the three own2-04 runs did not mention the docstring's IndexError rule, and two of them kept `page_count(0, n) == 1` on purpose. So the hand measure from pilot 4, "documented defect left in the edited file and not mentioned", is 3/30 in both arms, all on the pager task.

## What the plugin did (process table, `process.csv`, from each run's `.sw-home`)

| | runs |
|---|---|
| `sw run new`, plan with a `$` check, test file frozen, receipt taken, step certified | 20/30 |
| no run, no plan, no receipt; the final message says so ("I skipped the Stillwright run, plan and receipt for this one-line change") | 10/30 |
| a card opened | 1/30 (a notify card, own2-07 set 1, with a goal and no plan) |
| a run that stopped on a card nobody could answer | 0/30 |

Every certified check was the agent's own `python -m pytest tests`, the visible suite. On own2-01 and own2-04 the plugin therefore certified a shallow fix: the receipt proves the check the agent chose, and the agent chose the test it could see. No run froze or checked anything the plain arm did not already run. The ten skips split by task, not by set: own2-08 (recipe 4, 19 visible tests) skipped 3/3; own2-01, own2-02, own2-03, own2-05, own2-07, own2-09 and own2-10 skipped once each. The skill's rule that small goals still get a check (added 2026-10-29) held in two thirds of the runs. In 12 of the 20 certified runs the final message adds "there is no git repository here, so the receipt isn't tied to the files": the task folders are not git repositories, so the tree hash in every receipt is `none`, which is a harness limit recorded earlier and still open.

## Reading (pre-registered in the design note)
- The headline is the two costs and the ratio: **1.85 (1.74–2.08)**. No threshold turns it into a claim; this is the number.
- The adherence condition ("skipped plan and check on half or more of the runs") was not met: 10/30 skipped. The result is not explained away by the skill not running; where it ran, it cost more and certified the same visible suite.
- own2-01 and own2-04 did not change: the receipt and the reviewer gate did not turn a shallow fix into a reported gap or a pass. The with-arm's own2-01 was 3/3 false_done against the plain arm's 2/3; with n = 3 per task that is noise, and it is reported as such.
- Next step per the design note: the result goes to Hamza before any real run is planned. What it says about Stillwright on this task family is plain: on a one-file task with one visible test, the plugin adds planning, freezing and a receipt around the same pytest call, costs about 85% more per verified pass, and proves nothing the plain arm did not already show. The receipt's value, if it has one, is on work where the check is not the one visible test, and that is not what these tasks are.

## Limits
- Route B, local sandbox, same as pilots 1–4. The plain arm was measured a few hours earlier.
- Ten tasks, one file each, one visible test each: the cost ratio is for this shape of work only. The task folders are not git repositories, so receipts carry no tree hash; the plugin's git-bound guarantees were not exercised.
- Notional costs from the subscription receipts; the price table is the one Claude Code reports.
- The author of the tasks wrote the plugin. The pre-registered measures and the committed data are the mitigation; the number is not the one the author hoped for, which is some evidence the pre-registration held.
