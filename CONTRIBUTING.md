# Contributing

- Skills follow the Agent Skills spec: `skills/<name>/SKILL.md`, name matches folder.
- Keep skills short and explain *why*, not just *what*.
- Before a PR: `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo build --release`,
  `python3 -m unittest discover -s tests` (black-box tests against the binary) and
  `python3 scripts/validate_skills.py`.
- Bump `VERSION`, `Cargo.toml` and every manifest together; the validator checks they match.
