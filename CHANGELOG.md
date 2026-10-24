# Changelog

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
