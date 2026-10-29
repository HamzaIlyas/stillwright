# Cost: measure it, don't assume it

Most "saves 50%" claims around coding agents come without a method. Stillwright's rule is the
same for cost as for work: a number counts when a run produced it. This page is how to get one.

## What a run costs, in dollars

1. Put current prices in `~/.stillwright/prices.json` (copy `docs/prices.example.json`, check
   it against your vendor's pricing page; sw never guesses a price).
2. Log usage on steps as they finish: `sw run log latest step=2 model=claude-haiku-4-5 in=12000 out=900`
   (`in`/`out` from the harness's usage report for that subagent or turn; the step's result
   comes from `sw run done` or from a reviewer's `result=pass evidence=<file>`).
3. `sw run cost` sums the run per model and refuses to total a model it has no price for.

Claude Code also reports the session's own spend: `/usage` shows dollars per model and the
cache-hit rate; `claude -p ... --output-format json` returns `total_cost_usd` and per-model
tokens, which is what the eval harness reads.

## Who broke the cache?

`sw cache ~/.claude/projects/<project>/<session>.jsonl` reads a Claude Code session transcript
and lists the turns that rewrote a large prefix instead of reading it, with the likely cause
(a model switch, an expired cache after a pause, compaction or a settings change, or a big
block of new content) and, with prices set, an upper bound on what those rewrites cost over
cache-read price; genuinely new content could never have been a read, so it is a bound.

## A/B: does a tool actually save money?

`docs/evals/run_eval.py` runs the same task folders through `claude -p` twice, once with a
plugin/hook/setting and once without, and keeps each session's receipt (`result.json`: cost,
tokens by model, duration, turns). Grade the outputs the same way on both sides, then compare
dollars. Three one-sitting tasks are enough to catch a tool that costs more; showing a saving
needs tasks long enough for context and rework to matter.

What the harness showed for Stillwright itself (2026-10-26, three small tasks): about the same
cost as a plain agent, same completion, shorter reports. No saving on tasks
that small; details in [evals.md](evals.md).

## Tools worth using (vetted; see the scout's list)

- **codeburn** (github.com/getagentseal/codeburn, MIT): `codeburn guard install` adds hooks
  that warn at $5 and stop at $15 per session; `codeburn audit` explains where the money went.
  Local only. Recommended for any unattended run.
- **ccusage** (github.com/ccusage/ccusage, MIT): `ccusage statusline` puts spend and cache-hit rate in
  the status line; reads the local session files; covers Claude Code, Codex, OpenCode, Gemini CLI.
- **rtk** (github.com/rtk-ai/rtk, Apache-2.0 edition `rtk-oss`): shortens shell output before
  it reaches the model. The one independently measured saver, and it is about 5% with a
  one-point drop in pass rate (Quesma, Terminal-Bench 2.1). Use it when logs are long.

Avoid routers that take your API key or relay through third parties: a gateway that drops
`cache_control` makes every turn full price, and the "savings" come from reselling.

## What actually moves the bill (from Anthropic's docs)

- **Prompt caching does most of the work.** A cache read costs a tenth of a fresh input token on Haiku and a twentieth on Sonnet and Opus 5.5.
  The prefix must stay byte-stable: never switch the main model or effort mid-session, don't
  add or remove MCP servers mid-run, keep skill text stable, and compact only at step
  boundaries. Plugins that ship MCP servers invalidate the cache; skills and hooks don't.
- **Cheap models for cheap steps.** Use the small model in subagents (`sw-worker`), never by
  switching the main conversation, which re-reads the whole context uncached.
- **Less in context.** Pipe long output through `tail`/`grep`, read only the lines a step
  needs, let subagents return answers instead of transcripts.
- **Fewer retries.** A check that runs before the next step is cheaper than discovering the
  mistake three steps later; run low effort first and retry failures at high.
