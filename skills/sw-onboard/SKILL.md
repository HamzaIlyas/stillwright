---
name: sw-onboard
description: Stillwright's get-to-know-you step. Learns who the user is, what they're building, their goals, constraints and how they want to be talked to, in a few short rounds, then writes the profile and first goals so Stillwright can work alone afterwards. Use the first time Stillwright runs (no ~/.stillwright/profile.md), when the user says "get to know me", "update my profile", "my goals changed", or when stored facts clearly no longer fit.
license: MIT
metadata:
  author: Hamza Ilyas
  version: "0.1.5"
---

# Onboard

`sw` below is the Stillwright binary. If `sw` is not on PATH, follow the install note in the `stillwright` skill (ask the user first; never install unattended).

Goal: enough understanding to work for days without asking basic questions, gathered in
**at most three short rounds**. People quit long questionnaires, so look first and ask second.

## Round 0: look before asking (no questions yet)

Gather what is already visible, with permission-free reads only: the current repo (README,
git log, languages), other project folders the user points to, existing agent memory
(CLAUDE.md, AGENTS.md, memory files), and installed skills and agents. Draft the profile from
this. Every drafted line is a guess until the user confirms it.

## Rounds 1-3: ask only what you could not see

One message per round, at most 4 questions, each with your best guess pre-filled so the user
can just say "yes". Cover, in this order:

1. Who they are and what they're working toward (role, main projects, 3-month goals).
2. Boundaries: what never to touch, what always needs their OK, budget for paid tools/APIs.
3. How to talk: length, language, when to interrupt, preferred channel.
4. First goals: two or three concrete things to start on.

Stop as soon as answers repeat your guesses. Don't ask what you can find out yourself.

## Write it down

- `profile.md` in `sw home`: only what the user said or confirmed. Sections: About, Projects,
  Goals, Boundaries, Talk style, Tools they like. Short lines.
- Each first goal: `sw goal add "<goal>" --priority <1-5>`.
- Anything you inferred but did not confirm: `sw note add "<fact>" --source "<where seen>"`.

Finish with one line: what you'll start on first.

## Updating later

When the user corrects something, edit `profile.md` and retire any note it contradicts
(`sw note retire <id> --reason "..."`). Never quietly keep both.
