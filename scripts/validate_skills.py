#!/usr/bin/env python3
"""Check every skills/*/SKILL.md against the Agent Skills spec (agentskills.io/specification)
and check the plugin manifests agree with each other. Exits 1 on any problem."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    fields, key = {}, None
    for line in match.group(1).splitlines():
        top = re.match(r"^([a-z-]+):\s?(.*)$", line)
        if top:
            key, value = top.groups()
            fields[key] = value.strip().strip('"')
        elif key and line.startswith(" "):
            fields[key] += "\n" + line
    return fields


def check_skill(folder: pathlib.Path) -> list:
    problems = []
    skill = folder / "SKILL.md"
    if not skill.exists():
        return [f"{folder.name}: missing SKILL.md"]
    text = skill.read_text(encoding="utf-8")
    fm = frontmatter(text)
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not NAME.match(name) or len(name) > 64:
        problems.append(f"{folder.name}: invalid name {name!r}")
    if name != folder.name:
        problems.append(f"{folder.name}: name {name!r} does not match folder")
    if not 1 <= len(desc) <= 1024:
        problems.append(f"{folder.name}: description length {len(desc)} (must be 1-1024)")
    if len(text.splitlines()) > 500:
        problems.append(f"{folder.name}: SKILL.md over 500 lines")
    for ref in re.findall(r"\]\(((?:references|scripts|assets)/[^)]+)\)", text):
        if not (folder / ref).exists():
            problems.append(f"{folder.name}: broken link {ref}")
    return problems


def check_manifests() -> list:
    problems = []
    version = (ROOT / "VERSION").read_text().strip()
    manifests = {
        "plugin.json": json.loads((ROOT / "plugin.json").read_text()),
        ".claude-plugin/plugin.json": json.loads((ROOT / ".claude-plugin/plugin.json").read_text()),
        ".codex-plugin/plugin.json": json.loads((ROOT / ".codex-plugin/plugin.json").read_text()),
        "gemini-extension.json": json.loads((ROOT / "gemini-extension.json").read_text()),
    }
    for path, data in manifests.items():
        if data.get("name") != "stillwright":
            problems.append(f"{path}: name must be 'stillwright'")
        if data.get("version") != version:
            problems.append(f"{path}: version {data.get('version')} != VERSION {version}")
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    if not any(p.get("name") == "stillwright" for p in market.get("plugins", [])):
        problems.append("marketplace.json: stillwright plugin missing")
    installer = (ROOT / "skills/stillwright/scripts/get-sw.sh").read_text()
    if f'VERSION="{version}"' not in installer:
        problems.append("get-sw.sh: pinned VERSION does not match VERSION file")
    cargo = (ROOT / "Cargo.toml").read_text()
    if f'\nversion = "{version}"' not in cargo:
        problems.append("Cargo.toml: version does not match VERSION")
    return problems


def main() -> None:
    folders = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    problems = [p for f in folders for p in check_skill(f)] + check_manifests()
    for p in problems:
        print("FAIL", p)
    print(f"{len(folders)} skills checked, {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
