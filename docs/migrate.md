# Coming from OpenClaw or Hermes

Stillwright is not a replacement for either. Both are full agents with their own runtime;
Stillwright is a set of skills plus a small state tool that runs *inside* the agent you
already use. You can keep OpenClaw or Hermes and add Stillwright, or bring its habits to a
plainer agent such as Claude Code or Codex. This page maps the ideas.

## If you use OpenClaw

| OpenClaw | Stillwright |
|---|---|
| Skills in SKILL.md format (ClawHub) | Same format ([Agent Skills](https://agentskills.io)); `npx skills add HamzaIlyas/stillwright` or drop the `skills/` folder in |
| Heartbeat: a checklist re-run every 30 minutes by default, plus cron jobs ([docs](https://docs.openclaw.ai/gateway/heartbeat)) | One scheduled loop per hour at most: `claude -p "Use the stillwright skill: run one loop, then stop."` from cron. A loop with nothing to do writes and sends nothing |
| `HEARTBEAT_OK` / no reply when there is nothing to say | Same idea, made the default: silence unless a card is worth sending |
| Messages to you over chat gateways | A typed inbox (`ask`, `review`, `notify`, `idea`) you read with `sw inbox list`; the agent records your answers |
| Skills installed from the hub run with the agent's permissions | Tools are vetted by reading their code, approved by you once, then pinned by hash (`sw tool check` stops a run if one changed) |

What you lose: the chat gateways and always-on process. Stillwright has none; your agent's
own scheduling does that job.

## If you use Hermes Agent

| Hermes | Stillwright |
|---|---|
| Skills under `~/.hermes/skills/<group>/<skill>/` ([docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)) | Drop Stillwright's `skills/` into `~/.hermes/skills/stillwright/` (README has the one-liner); Hermes picks them up on the next message |
| Cron jobs with results sent to Telegram, Slack and others | A scheduled loop; results as inbox cards, or forward the `notify` card text from your own script |
| A user model and full-text memory of past sessions | `profile.md` (what you said) kept apart from `notes.json` (what it inferred, each with a source and date, retired when contradicted) |
| The agent writes and improves its own skills after hard tasks | `sw-forge` builds a skill when nothing fits, tests it, and installs only after your `review` card |

What you lose: Hermes' messaging integrations and its richer memory search. Stillwright
keeps state as plain files you can read, grep and delete.

## In both cases

- Install `sw` (one binary) and the skills; see the [quickstart](quickstart.md).
- Run `sw-onboard` once so the profile exists; after that it works from your goals.
- Keep your existing agent's unattended rules in mind: Stillwright never pushes, deploys,
  publishes, sends or installs anything new while nobody is watching.

If a mapping above is wrong for a newer OpenClaw or Hermes release, open an
[issue](https://github.com/HamzaIlyas/stillwright/issues/new?template=bug.yml) with the doc link.
