# Press kit

Everything here may be used to write or record about Stillwright. No permission needed;
a link back to github.com/HamzaIlyas/stillwright is appreciated.

## One paragraph

Stillwright is an open-source orchestrator that runs inside the AI agent you already use
(Claude Code, Codex, Gemini CLI, Cursor, Copilot and others). It gets to know you, then works
on your goals: it plans each one, vets tools by reading their code before trusting them, and
passes a step only when an independent check proves it. It speaks only when it needs you, in
five lines or fewer. State is plain files; the CLI is one Rust binary. MIT.

## Three angles

- Quiet versus noisy agents: the inbox has four card types and silence is the default.
- Proof, not claims: every step has a check fixed before the work; a fresh reviewer, not the
  worker, decides. Measured on three tasks: [docs/evals.md](../docs/evals.md).
- Tools you can trust: found by evidence, read before use, approved once, pinned by hash.

## Files

- `logo.svg`, `logo.png` (dark), `logo-light.svg`, `logo-light.png`
- `card.png`: 1280×640 social card
- `demo-horizontal.mp4` (960×560, 18 s), `demo-vertical.mp4` (720×1280, 18 s), and
  `../assets/demo.gif`
- Colours: ink `#12211a`, text `#e5ede7`, accent `#3cc38b`, muted `#93a39a`

## Try it in two minutes

```sh
pip install stillwright
npx skills add HamzaIlyas/stillwright
sw status
```

Then, in your agent: "Use the stillwright skill." It asks a few short questions once, then
works from your goals. Give it something real, for example: "Make the failing test in this
repo pass and prove it." Watch `sw run status latest` and `sw inbox list` from another
terminal.

## Five prompts that show it off

1. "Stillwright: fix the flaky test in tests/ and prove it passes 20 times."
2. "Stillwright: find the best maintained library for X, vet it, and tell me in five lines."
3. "Stillwright: rewrite README.md in plain English, keep every fact, no marketing words."
4. "Stillwright: what's new that matters for this project? Only cards worth my time."
5. "Stillwright: run one loop, then stop." (from cron, while you are away)

## Facts you can check

- Releases: github.com/HamzaIlyas/stillwright/releases; PyPI: pypi.org/project/stillwright
- Evals with raw runs: docs/evals.md
- Every `sw` command in the docs is executed by CI (scripts/check_docs.py)
