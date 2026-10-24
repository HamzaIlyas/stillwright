# Quickstart

Ten minutes from nothing to a first proven run. Every `sw` command on this page is executed
by CI against the current binary, so if it is here, it works.

## 1. Install the skills into your agent

Pick your agent in the [README install table](../README.md#install). For Claude Code:

```sh
claude plugin marketplace add HamzaIlyas/stillwright
claude plugin install stillwright@stillwright
```

## 2. Install `sw`

Linux and macOS:

```sh
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/HamzaIlyas/stillwright/releases/latest/download/stillwright-installer.sh | sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/HamzaIlyas/stillwright/releases/latest/download/stillwright-installer.ps1 | iex"
```

Open a new shell, then:

```sh
sw --version
sw status
```

`status` says `profile: missing, run onboarding`. That is expected: nothing knows you yet.

## 3. First conversation

In your agent, say:

> Use the stillwright skill.

It runs `sw-onboard`: it looks at your repo and existing notes first, then asks at most three
short rounds of questions, writes `~/.stillwright/profile.md`, and adds your first goals.
You can also add goals yourself:

```sh
sw goal add "Fix the flaky login test" --priority 1
sw goal add "Write the October changelog"
sw goal list
```

## 4. Let it work

Say "stillwright" or give it a goal. It plans in a run folder, shows you the plan if it has
outward actions, does the work, and verifies each step. Watch from outside at any time:

```sh
sw status
sw run list
sw run status latest   # may fail
```

`run status latest` says `no runs yet` until the agent has started its first run.

## 5. Your inbox

The agent speaks to you only through cards. Nothing to show means nothing is shown.

```sh
sw inbox list
sw inbox add review "Example card: publish the release?" --body "Shown here so you can see one"
sw inbox show 1
sw inbox answer 1 "yes"
sw inbox close 1
```

In practice the agent adds the cards and you answer them in chat; it records your answer
and closes the card once applied.

## 6. Keep it running while you're away

Schedule one loop per hour, for example from cron on Linux/macOS:

```
0 * * * * cd ~/work && claude -p "Use the stillwright skill: run one loop, then stop."
```

Unattended runs never push, deploy, publish, send or install anything new. Those wait as
review cards for when you're back. Details: [unattended runs](../skills/stillwright/references/unattended.md).

## Where things live

```
~/.stillwright/
  profile.md        what you told it
  notes.json        what it learned, each with a source and date
  goals.json        the queue
  inbox.json        the cards
  tools.lock.json   third-party tools it trusts, pinned by hash
  runs/<id>/        plan.md and log.jsonl per piece of work
```

Everything is plain text. Delete the folder and it forgets you.
