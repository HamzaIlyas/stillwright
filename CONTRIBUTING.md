# Contributing

- Skills follow the Agent Skills spec: `skills/<name>/SKILL.md`, name matches folder.
- Keep skills short and explain *why*, not just *what*.
- Before a PR: `python3 -m unittest discover -s tests` and `python3 scripts/validate_skills.py`.
- Bump `VERSION` and every manifest together; the validator checks they match.
