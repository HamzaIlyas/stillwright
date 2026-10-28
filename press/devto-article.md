---
title: I measured my agent orchestrator against a plain agent. Here is what held up and what didn't.
published: true
tags: ai, opensource, agents, productivity
canonical_url: https://huggingface.co/datasets/Folvix/stillwright-evals
cover_image: https://huggingface.co/spaces/Folvix/stillwright/resolve/main/img/card.png
---

Stillwright is a small open-source layer that runs inside the AI agent you already use
(Claude Code, Codex, Gemini CLI, Cursor and others). It plans a goal into steps, each with a
check decided before the work starts, lets a fresh reviewer rather than the worker decide
whether a step passed, and talks to you only through a short inbox. The pitch is "proof, not
claims". So the first thing I owed anyone was proof that it does anything.

## The test

Three small, real tasks, each done twice by a fresh agent of the same model (Claude Sonnet):
once told to follow the Stillwright skills, once with no skill at all.

- **Code**: make five unit tests pass in a tiny pricing module (one real bug: a discount could go negative), without touching the tests.
- **Writing**: rewrite a marketing paragraph into plain English, at most 80 words, keeping four facts exactly, no marketing adjectives.
- **Research**: find the latest version of a project on PyPI and on GitHub, say whether they match, give the release date, and cite a URL for every fact.

Grading was done by scripts where a script can decide (do the tests pass with the tests
unchanged, is the word count under 80, are the four facts present, is the version right) and by
a separate read-only model judge for one thing a script can't: does the report to the user
contain any false claim.

## Results

| Task | Side | task done | evidence in report | report ≤ 5 lines | plan + log | false claims | wall time | tokens |
|---|---|---|---|---|---|---|---|---|
| code | Stillwright | yes | yes | no (8) | yes | 0 | 107 s | 78k |
| code | plain | yes | yes | no (7) | no | 0 | 64 s | 71k |
| writing | Stillwright | yes | yes | no (8) | yes | 0 | 156 s | 86k |
| writing | plain | yes | yes | no (8) | no | 1 | 74 s | 71k |
| research | Stillwright | yes | yes | no (22) | yes | 0 | 147 s | 87k |
| research | plain | yes | yes | no (26) | no | 0 | 88 s | 73k |

## What held up

- **An auditable record.** Every Stillwright run left a plan with the check for each step
  written before the work, and a log with the check's output. None of the plain runs left anything.
- **No false claims.** The one false claim in the whole set came from the plain side: it
  said four facts were "kept exactly" after changing the wording (it did disclose the change
  in the same paragraph, so a mild one).
- **It caught its own mistake once.** In the writing task, Stillwright's first draft added two
  things nobody asked for. The fresh reviewer the skill requires failed that draft; the agent
  removed them; the log shows fail → fix → pass.

## What didn't

- **On tasks this small, the plain agent did the work just as well.** All six runs finished
  correctly, with evidence. Stillwright's value did not show up in "done".
- **It broke its own five-line rule every time** (8, 8 and 22 lines). The one-line inbox
  cards were short; the report it returned was not. The plain side was just as long, but it
  had no such rule.
- **It costs more**: about 1.7–2x the wall time and 10–20% more tokens, spent on the plan,
  the checks and the reviewer.

## The fix, and the re-run

The five-line failure came from the skill text: it told the agent to write a short card, then
let it write a long report after the card. I changed one passage so the final message *is*
the card's text, and told two helper skills to keep their reports inside the limit. The three
Stillwright runs were repeated with the changed skill (the plain side didn't change, so it
wasn't re-run):

| Task | task done | evidence | report ≤ 5 lines | plan + log | wall time | tokens |
|---|---|---|---|---|---|---|
| code | yes | yes | yes (4) | yes | 33 s | 76k |
| writing | yes | yes | yes (3) | yes | 40 s | 77k |
| research | yes | yes | yes (4) | yes | 53 s | 79k |

All three now meet the rule with the proof still in the message. Wall time also dropped to
about half of the plain runs' first-round times; one re-run is not enough to call that real.

## Then I measured money instead of tokens

Token counts from inside a harness are not a bill. So I ran the same three tasks again as
headless `claude -p` sessions, where Claude Code itself reports the dollars: with Stillwright
$0.92 in total, without $0.80. Both sides finished every task. No saving, and I am not going
to describe it as one. Two earlier priced rounds had to be thrown away because my harness had
denied the agents permission to run tests; those receipts measured permission failures.

While checking what the popular cost-saving tools actually measure, I found that the ones
claiming 30–50% publish no method, and the one with an independent measurement saves about
5%. So the thing worth shipping was the measuring: an A/B cost harness, `sw run cost`
(dollars per run at prices you set), and `sw cache`, which reads a session transcript and
names the turns that rewrote the prompt cache. On one 523-turn session of mine it found
4.5 million tokens rewritten at 15 break points: pauses long enough for the cache to expire,
large new content, and one model switch.
All of it is in the dataset and in `docs/cost.md`.

## What this does and doesn't show

Three tasks, one run each per side, same model on both sides, tasks that fit in a single
sitting. Stillwright is built for long, multi-step work with outward actions and unattended
runs, and none of that was exercised here. The grading script and the judge prompt were
written by me, the author. The raw run folders, the plans and logs, the grading script, the timing of each run and the
judge's full report are all in the repository, so anyone can re-grade or dispute them:
[github.com/HamzaIlyas/stillwright](https://github.com/HamzaIlyas/stillwright), [docs/evals.md](https://github.com/HamzaIlyas/stillwright/blob/main/docs/evals.md); the raw runs and grading script are also on [Hugging Face](https://huggingface.co/datasets/Folvix/stillwright-evals).

The honest summary: on small tasks it doesn't make the agent more capable or cheaper; it makes
the agent's work checkable, keeps it from claiming things it didn't do, and now gives you the
tools to check anyone's cost claim, including mine.

Install: `pip install stillwright` and `npx skills add HamzaIlyas/stillwright`. MIT.
