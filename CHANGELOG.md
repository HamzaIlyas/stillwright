# Changelog

## Unreleased
- Homebrew: `brew install HamzaIlyas/tap/stillwright` (formula published to HamzaIlyas/homebrew-tap on each release).
- sw-forge: forge only on logged triggers, evidence file required, old-vs-new eval before install, rollback copy, usage tracking and a retire card (design from SkillsBench, Hermes, Prime Agent, ECC, skill-creator).

## 0.1.3 - 2026-10-24
- press/ kit (logo, social card, horizontal and vertical demo clips, pitch, prompts) and docs/migrate.md (from OpenClaw or Hermes).
- `sw init`: writes the repo-level settings that turn Stillwright on by default in Claude Code and GitHub Copilot.
- README: `npx plugins add` / `npx skills add` one-liners; `.agents/skills` mirror; GitHub topics for the Gemini gallery.

## 0.1.2 - 2026-10-24
- docs/evals.md: re-run after the skill change; all three runs within five lines.
- sw-scout: references/vetted-tools.md, a checked starter list with an avoid list.
- stillwright skill: the final message is the notify card text; five-line rule applies to it (gap found by the eval).
- docs/evals.md: first measured comparison against a plain agent, with raw runs and grading script.
- `pip install stillwright` (published to PyPI from 0.1.1).
- Hermes Agent install row (drop-in to ~/.hermes/skills/).

## 0.1.1 - 2026-10-24
- README: badges, cited research behind each rule, Folvix link; issue and PR templates.
- Codex-native marketplace file (.agents/plugins/marketplace.json); install table covers Cursor and OpenCode.
- docs/quickstart.md, verified by scripts/check_docs.py in CI; examples/quickstart-run with the real run state.
- docs/troubleshooting.md and docs/windows.md.
- Demo GIF in README; `pip install stillwright` packaging (maturin) with a PyPI Trusted Publishing workflow.

## 0.1.0 - 2026-10-23
- First release: the `stillwright` loop and eight `sw-*` skills.
- `sw` state keeper in Rust: goals, runs, inbox, notes with validity, hash-pinned tools.
- Packaging for Claude Code, Codex, Gemini CLI and Agent Skills agents.
