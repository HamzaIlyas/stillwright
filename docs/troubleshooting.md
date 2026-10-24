# Troubleshooting

Each entry is a message you can actually see, what it means, and what to do.

## `sw: command not found` right after installing

The installer puts `sw` in `~/.cargo/bin` and adds it to your shell profile, but the shell
you're in doesn't know yet. Open a new terminal, or run `source ~/.cargo/env`.

## `profile: missing, run onboarding`

Normal on a fresh machine. In your agent, say "use the stillwright skill"; it runs
`sw-onboard` and writes `~/.stillwright/profile.md`. Check with:

```sh
sw status
```

## `... is not valid JSON (...); fix or move it aside, then retry`

A state file (`goals.json`, `inbox.json`, `notes.json` or `tools.lock.json`) was edited by hand
or truncated. Open it, fix the JSON, or move it away to start that file empty. `sw` never
guesses: it refuses rather than risk losing data.

## `cannot lock state: ...`

Two `sw` processes are running at once (for example a scheduled run and your own command) and
the lock could not be taken. Wait a moment and retry. On Windows this appeared as
`Access is denied (os error 5)` in builds before 0.1.0; update if you see it.

## `<tool> changed since it was pinned; re-vet it, then pin again with --force`

A pinned third-party tool's files changed on disk. That is the point of pinning. Read what
changed, decide whether you still trust it, and only then:

```sh
sw tool pin example-tool /tmp/example-tool --force   # may fail
```

(The line above fails here because `/tmp/example-tool` does not exist; use your tool's path.)

## `sw tool check` exits 1 with `CHANGED` or `MISSING`

Same situation from the other side: a scheduled run calls `tool check` before using tools,
and stops at the first changed one. Re-vet and re-pin, or remove the tool's line from
`~/.stillwright/tools.lock.json`.

## `no runs yet` / `write plan.md`

`sw run status` found no run, or a run folder without a `plan.md`. The agent creates both; if
you see this mid-task, the agent stopped before planning. Ask it to continue.

## `x is not a run folder under .../runs`

`sw run log <path>` only accepts folders inside `~/.stillwright/runs/`, so a typo can't
write a log into your project. Use the run's name, its slug, or `latest`.

## `inbox N is closed, only open cards can be answered`

The card was already closed. Add a new card or re-open the topic with the agent.

## The agent keeps asking instead of working

Check the inbox: an unanswered `ask` or `review` card blocks the step that needs it.

```sh
sw inbox list
```

Answer in chat (the agent records it with `sw inbox answer`), or answer it yourself and tell
the agent.

## Nothing happens in scheduled runs

By design a run with nothing to do writes and sends nothing. Confirm it ran with:

```sh
sw run list
```

If the list doesn't grow, check the scheduler itself (cron logs, the routine's run history).
Unattended runs also stop, silently, when `sw` is missing or a pinned tool changed; both
leave a card or a log line explaining why.

## Still stuck

Open a [bug](https://github.com/HamzaIlyas/stillwright/issues/new?template=bug.yml) with the
exact message and the output of `sw status`.
