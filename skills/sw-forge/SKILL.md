---
name: sw-forge
description: Builds a new skill (or small script or tool) when sw-scout finds nothing good enough, tests it on real cases, and installs it so Stillwright can reuse it. Also turns a hard task that just succeeded into a reusable skill. Use when no existing tool fits a need, when the same multi-step work has been done twice, or when the user says "make a skill/tool for this".
license: MIT
metadata:
  author: Hamza Ilyas
  version: "0.1.0"
---

# Forge

`sw` below means the `sw` command if installed with pip; otherwise `python3 <SW>`, where `<SW>` is the absolute path of `stillwright/scripts/sw.py` in the same skills folder as this skill (resolve it once from this skill's own location, not the working directory).

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

## 3. Test it for real

Write 2-3 realistic prompts or inputs, including one edge case. Run them in fresh subagents
with the skill, and check the outputs against the need's check. Fix and rerun until they pass.
Scripts get unit tests.

## 4. Ask, then install

Add a `review` card: the skill's name, what it does, the test evidence, where it will be
installed (Claude Code: `~/.claude/skills/`; others: `~/.agents/skills/` or the harness's
documented path), in at most 4 lines. Only after a yes: copy it there and
`sw tool pin <name> <installed path> --source forged`.

Unattended runs may build and test a skill, but installing always waits for the card.

## Learning from success

After a hard task succeeds (several retries, or a new kind of work), ask: would the next
person need the same steps? If so, forge a skill from what worked, including the pitfalls hit.
