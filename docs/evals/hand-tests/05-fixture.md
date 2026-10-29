# Hand test 5: the with-arm with a profile fixture

Date: 2026-10-29. Same flags as hand test 3; `docs/evals/harness/fixture/{profile.md,guards.md}` copied into the per-run `STILLWRIGHT_HOME` in both arms (the plain arm never reads it). With-arm prompt prefixed with `/stillwright `. One run on the control task.

## Result
- Verdict pass, no tamper, 4 turns, 22.2 s, 0.0724 USD, only `claude-sonnet-5-5` billed.
- The skill fired: in `-p` mode the `/stillwright` prefix expands the skill into the prompt (no `Skill` tool call appears), and the first command was `which sw; sw status`, which answered `profile: yes | goals: 0 open | inbox: ask 0, review 0, notify 0, idea 0`. So the fixture is read and the "no profile, needs onboarding" stop from hand test 3 is gone.
- Then the agent fixed the bug with `sed`, ran the suite, and wrote: "I skipped the Stillwright plan and run log because this was a one-line fix." No `sw run new`, no plan, no `$` check, no receipt; `.sw-home/runs/` stayed empty.

## Finding
With the fixture the skill runs, but on a one-step task the model chooses not to use Stillwright's mechanisms (plan, check, receipt, reviewer). The skill text gives no rule for tiny goals, so the model decides, and it decides to skip. The eval tasks are all this size. Measured as is, the with-arm would be the plain arm plus a `sw status` call.

## Decision needed (Hamza)
Either (a) measure the skill as it is, expecting little or no difference on one-step tasks and saying so, or (b) add one rule to the skill before pre-registration: "a goal that comes with tests or a check command gets a run and a `$` check, however small", then measure that. (b) is a product change made before the eval and recorded as such; it is the behaviour the eval is meant to test.

## Status
Fixture works; certified. The skill-size rule is an open decision.
