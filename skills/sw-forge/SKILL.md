---
name: sw-forge
description: Builds a new skill (or small script or tool) when sw-scout finds nothing good enough, tests it on real cases, and installs it so Stillwright can reuse it. Also turns a hard task that just succeeded into a reusable skill. Use when no existing tool fits a need, when the same multi-step work has been done twice, or when the user says "make a skill/tool for this".
license: MIT
metadata:
  author: Hamza Ilyas
  version: "0.1.3"
---

# Forge

`sw` below is the Stillwright binary. If `sw` is not on PATH, follow the install note in the `stillwright` skill (ask the user first; never install unattended).

Build the smallest thing that passes the need's check. A forged skill is code we vouch for,
so it's held to the same proof rules as everything else.

## 1. Confirm the gap

Scout's report shows nothing that passes, or the need is specific to this user. If a
candidate almost fits, prefer a thin wrapper around it over a rewrite.

## 2. Write it to the Agent Skills standard

Folder `<name>/` with `SKILL.md` (frontmatter: `name` matching the folder, lowercase-hyphen,
max 64 chars; `description` max 1024 chars, saying what it does **and when to use it**),
plus `scripts/` for anything deterministic. The body explains *why* as well as *what*, stays
under ~200 lines, and moves detail into `references/`. Only the standard library or
dependencies already installed, unless the user approves more.

Build it in the run folder first, never straight into a live skills folder: a skill there
loads into every future session.

## 3. Prove it before anyone installs it

Skills a model writes for itself are not useful by default: in a 2026 benchmark, curated
skills raised pass rates by about 16 points while skills the models wrote before each task
averaged 1.3 points *below* having no skill, and a study of self-evolving skills found that
only a minority of candidates ever set a validated best, with validation and final results
sometimes disagreeing (sources in [references/evidence-rules.md](references/evidence-rules.md)). So a forged skill earns its
place with numbers, not with the feeling that it is useful.

1. Write 2-3 realistic prompts, including one edge case, into `evals/evals.json` inside the
   skill folder (the skill-creator format: `prompt` plus a short expected outcome).
2. Run each prompt twice in fresh subagents: once with the new skill, once with the baseline
   (no skill for a new one; for a patch, the previous version kept under
   `~/.stillwright/forge/<name>/prev/`, outside the pinned folder).
3. Grade each run with the need's own check command, or with a fresh read-only reviewer that
   did not write the skill (the rule from `sw-verify`), and quote the outcome into the run log:
   `sw run log latest step=N check="evals old vs new" result=pass|fail note="new 3/3, baseline 1/3, tokens +8%"`.
4. The skill goes forward only if it is better on at least one prompt and worse on none, or
   equal everywhere with fewer retries or tokens. A plain tie is not enough. Otherwise fix and
   rerun, or drop it and log why.

Scripts get unit tests as well.

## 4. Ask, then install

Add a `review` card, at most 5 lines: the skill's name, what it does, the trigger that
produced it, the old-vs-new numbers, and the install path (Claude Code: `~/.claude/skills/`;
others: `~/.agents/skills/` or the harness's documented path). Only after a yes:

- copy it there; for a patch, first copy the installed version to
  `~/.stillwright/forge/<name>/prev/` so it can be put back;
- `sw tool pin <name> <installed path> --source forged` (a patch re-pins with `--force`, after
  its own card);
- record the install: `sw note add "<name>: installed from <run slug>, baseline <n>/<m> -> <n>/<m>" --kind fact --source forge`.

Unattended runs may build and test a skill, but installing always waits for the card.

## 5. Watch it, and let it go

Every later use logs `tool=<name>` with the step's result. Keep the score in a note
(`sw note add "<name>: used 4, passed 3" --source forge`, retiring the old count). Two failed
uses in a row, or 90 days without a use, raise a `review` card that proposes removing the
skill with the numbers. Never remove one without the card. A skill that has not cut retries
or subagent calls on its kind of step after three uses gets the same card.

## When to forge at all

Only on one of three logged triggers, so skills come from evidence rather than enthusiasm:

- a step passed after two or more retries (the fix is worth keeping);
- the user corrected the approach;
- the same multi-step work was done twice.

Log the trigger when you see it: `sw run log latest event=forge-candidate reason=retries|correction|repeat note="<what>"`.
Every forged skill carries `references/evidence.md`: the run slug, the steps, and the
failing-then-passing check output that justified it. No evidence file, no install.

Keep `SKILL.md` itself free of the incident story: one procedure, the pitfalls as rules, under
200 lines. The story lives in the evidence file.
