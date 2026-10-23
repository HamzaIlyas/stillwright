# Running unattended

Stillwright works the same with or without the user watching. Without them, these extra
rules apply.

## Ways to schedule a run

Each run is one non-interactive session that starts with: "Use the stillwright skill: run one
loop, then stop."

- **cron / launchd / systemd timer** calling the harness in print mode, for example
  `claude -p "Use the stillwright skill: run one loop, then stop."` from the project folder.
- **Claude Code routines** (cloud schedules, GitHub events, or an API call). A routine
  has no human in the loop, so the prompt must stand on its own.
- **`/loop`** inside an open Claude Code session, for short periods while the user is around.
- **CI** (GitHub Actions on a schedule) for repo-scoped goals. Keep secrets in the CI store.

Hourly at most. Each run should do one goal step or one radar pass, not everything.

## Rules with nobody watching

- No outward actions at all. Add a `review` card and move to other work.
- No new third-party tools. A scouted tool waits as a `review` card until approved.
- No new installed skills. A forged skill may be built and tested, but installing it waits for its card.
- Budget per run is half the interactive default.
- An empty run (nothing to do, nothing changed) writes nothing and sends nothing.
- Every run ends with the run log updated, so the next session can resume without guessing.
- If `sw tool check` reports a changed tool, stop using it and add a `review` card.
