# Goal: a quickstart page exists and every `sw` command in it runs exit 0 against the release binary
1. Write docs/quickstart.md: install, first run, daily use, unattended | who: self | check: python3 scripts/check_docs.py docs/quickstart.md exits 0 | after: -
2. Add scripts/check_docs.py and run it in CI | who: self | check: grep -q check_docs .github/workflows/ci.yml | after: 1
3. Link the quickstart from README | who: self | check: grep -q "docs/quickstart.md" README.md | after: 1
Outward: none (push waits for the usual audit and review)
