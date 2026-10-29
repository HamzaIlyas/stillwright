# Hand test 1: a clean baseline on the subscription, without a second login

Date: 2026-10-29. Claude Code 2.1.308, macOS. Three tiny calls (one word each, pinned Haiku).

## Tried first: empty CLAUDE_CONFIG_DIR
Loads nothing from `~/.claude` (only `.claude.json`, `backups/`, `projects/`, `sessions/` are created), but the subscription login lives per config dir: `result: Not logged in`. Rejected: Hamza does not want a second login.

## Passed: normal config dir, settings switched off
```
DISABLE_AUTOUPDATER=1 claude -p "<prompt>" --model claude-haiku-4-5-20251001 \
  --setting-sources "" --strict-mcp-config \
  --output-format stream-json --verbose --no-session-persistence
```
`system/init` with these flags:
- `plugins`: only the three builtin ones (`cc-plugin-agents-md`, `cc-plugin-telemetry`, `cc-plugin-plugin-authoring`); superpowers, ECC and the rest absent.
- `agents`: 6 builtin (`claude`, `claude-code-guide`, `Explore`, `general-purpose`, `Plan`, `statusline-setup`); the 71 ECC agents absent.
- `skills` / `slash_commands`: 22 / 58 builtin.
- `mcp_servers`: 0 with `--strict-mcp-config` (7 claude.ai connectors without it).
- `apiKeySource: none`, so the subscription is used; `is_error: false`; `result: pong`.
- `modelUsage`: only `claude-haiku-4-5-20251001`. Without `--strict-mcp-config` a second model (`claude-haiku-5-5`) also appeared in the receipt, so MCP attachment adds background calls; the flag removes them.
- `memory_paths.auto` is derived from the cwd under `~/.claude/projects/`, so every run must get its own cwd (fresh temp dir), which also keeps auto-memory from carrying between runs.
- `cost: 0.0113 USD` for 10 input / 45 output tokens (subscription cost is notional).

## Consequence for the harness
Both arms run with exactly these flags from a fresh cwd; the with-arm adds `--plugin-dir <stillwright at the pinned commit>` and `STILLWRIGHT_HOME=<fresh per-run dir>`; the plain arm sets the same `STILLWRIGHT_HOME` and never uses it. `--bare` is not needed and not used (it would drop hooks and subagents and needs an API key).
