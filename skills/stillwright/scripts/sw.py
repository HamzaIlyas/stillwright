#!/usr/bin/env python3
"""sw: the state keeper for Stillwright. Plain files, no dependencies, Python 3.9+.

State lives in $STILLWRIGHT_HOME (default ~/.stillwright):
  profile.md        what the user told us (written during onboarding)
  notes.json        what we learned ourselves: dated, sourced, retired when contradicted
  goals.json        the work queue
  inbox.json        the only way we talk to the user: ask | review | notify | idea
  tools.lock.json   third-party tools we trust, pinned by content hash
  runs/<id>/        plan.md + log.jsonl per piece of work

Commands:
  sw status
  sw home
  sw goal add "<text>" [--priority 1-5] | list [--all] | done <id> [--note ...]
  sw run new <slug> [--goal <id>] | log <run|latest> key=value... | status [run|latest] | list
  sw inbox add <ask|review|notify|idea> "<title>" [--body ...] [--run ...] | list [--all] | show <id>
           | answer <id> "<answer>"   (the user's reply; stays visible until applied)
           | close <id> [--answer ...] (applied and done)
  sw note add "<fact>" --source "<where>" [--kind fact|preference|constraint] | list [--all] | retire <id> --reason "..."
  sw tool pin <name> <path> [--source <url>] [--force] | check | list
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
from contextlib import contextmanager

INBOX_KINDS = ("ask", "review", "notify", "idea")
NOTE_KINDS = ("fact", "preference", "constraint")
STEP_LINE = re.compile(r"^(\d+)\..*\|\s*check:", re.M)
HASH_SKIP = {".git", "__pycache__", "node_modules", ".DS_Store", ".venv"}


def home() -> pathlib.Path:
    root = pathlib.Path(os.environ.get("STILLWRIGHT_HOME") or pathlib.Path.home() / ".stillwright")
    (root / "runs").mkdir(parents=True, exist_ok=True)
    return root


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def load(name: str) -> list:
    path = home() / name
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError as err:
        sys.exit(f"{path} is not valid JSON ({err}); fix or move it aside, then retry")


def save(name: str, items: list) -> None:
    path = home() / name
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


@contextmanager
def locked():
    """Serialise read-modify-write so a scheduled run and a live session can't lose updates."""
    lock = open(home() / ".lock", "a+")
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        yield
    finally:
        lock.close()


def next_id(items: list) -> int:
    return max((i["id"] for i in items), default=0) + 1


def find(items: list, item_id: int) -> dict:
    for item in items:
        if item["id"] == item_id:
            return item
    sys.exit(f"no item with id {item_id}")


# goals -------------------------------------------------------------------

def goal_add(a):
    goals = load("goals.json")
    goal = {"id": next_id(goals), "text": a.text, "priority": a.priority, "status": "open", "created": now()}
    goals.append(goal)
    save("goals.json", goals)
    print(f"goal {goal['id']} added")


def goal_list(a):
    goals = [g for g in load("goals.json") if a.all or g["status"] == "open"]
    for g in sorted(goals, key=lambda g: (g["priority"], g["id"])):
        print(f"{g['id']}. [p{g['priority']}] {g['text']}" + ("" if g["status"] == "open" else f" ({g['status']})"))
    if not goals:
        print("no open goals")


def goal_done(a):
    goals = load("goals.json")
    goal = find(goals, a.id)
    goal.update(status="done", closed=now(), note=a.note or "")
    save("goals.json", goals)
    print(f"goal {a.id} done")


# runs --------------------------------------------------------------------

def resolve_run(ref: str) -> pathlib.Path:
    runs = sorted(p for p in (home() / "runs").iterdir() if p.is_dir())
    if ref in ("", "latest"):
        if not runs:
            sys.exit("no runs yet")
        return runs[-1]
    path = pathlib.Path(ref)
    if path.is_dir():
        return path
    matches = [p for p in runs if p.name == ref or p.name.endswith(ref)]
    if not matches:
        sys.exit(f"no run matching {ref}")
    return matches[-1]


def run_new(a):
    slug = re.sub(r"[^a-z0-9-]+", "-", a.slug.lower()).strip("-")[:40] or "run"
    base = home() / "runs" / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{slug}"
    run, n = base, 1
    while run.exists():
        n += 1
        run = base.with_name(f"{base.name}-{n}")
    run.mkdir(parents=True)
    (run / "log.jsonl").touch()
    if a.goal:
        log_event(run, {"event": "start", "goal": str(a.goal)})
    print(run)


def log_event(run: pathlib.Path, event: dict) -> None:
    with open(run / "log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), **event}, ensure_ascii=False) + "\n")


def run_log(a):
    event = {}
    for pair in a.pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            sys.exit(f"expected key=value, got {pair!r}")
        event[key] = value
    log_event(resolve_run(a.run), event)


def step_results(run: pathlib.Path) -> dict:
    results = {}
    for n, line in enumerate((run / "log.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                print(f"warning: {run.name}/log.jsonl line {n} is not JSON, skipped", file=sys.stderr)
                continue
            if "step" in e and "result" in e:
                results[str(e["step"])] = e["result"]
    return results


def next_step(run: pathlib.Path):
    plan = run / "plan.md"
    steps = STEP_LINE.findall(plan.read_text(encoding="utf-8")) if plan.exists() else []
    results = step_results(run)
    pending = [s for s in steps if results.get(s) != "pass"]
    return (pending[0] if pending else None), len(steps), results


def run_status(a):
    run = resolve_run(a.run)
    nxt, total, results = next_step(run)
    passed = sum(1 for r in results.values() if r == "pass")
    print(f"{run.name}: {passed}/{total} steps passed")
    for step, result in sorted(results.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
        if result != "pass":
            print(f"  step {step}: {result}")
    print("next:", f"step {nxt}" if nxt else ("write plan.md" if total == 0 else "none, all passed"))


def run_list(a):
    for run in sorted(p for p in (home() / "runs").iterdir() if p.is_dir())[-10:]:
        nxt, total, results = next_step(run)
        passed = sum(1 for r in results.values() if r == "pass")
        print(f"{run.name}  {passed}/{total}")


# inbox -------------------------------------------------------------------

def inbox_add(a):
    items = load("inbox.json")
    item = {"id": next_id(items), "kind": a.kind, "title": a.title, "body": a.body or "",
            "run": a.run or "", "status": "open", "created": now()}
    items.append(item)
    save("inbox.json", items)
    print(f"inbox {item['id']} ({a.kind}) added")


def inbox_list(a):
    items = [i for i in load("inbox.json") if a.all or i["status"] in ("open", "answered")]
    order = {k: n for n, k in enumerate(INBOX_KINDS)}
    for i in sorted(items, key=lambda i: (order[i["kind"]], i["id"])):
        print(f"{i['id']}. {i['kind']}: {i['title']}" + ("" if i["status"] == "open" else f" ({i['status']})"))
    if not items:
        print("inbox empty")


def inbox_show(a):
    item = find(load("inbox.json"), a.id)
    print(f"{item['id']}. {item['kind']}: {item['title']} ({item['status']})")
    for key in ("body", "answer", "run"):
        if item.get(key):
            print(f"{key}: {item[key]}")


def inbox_answer(a):
    items = load("inbox.json")
    item = find(items, a.id)
    item.update(status="answered", answer=a.answer, answered=now())
    save("inbox.json", items)
    print(f"inbox {a.id} answered")


def inbox_close(a):
    items = load("inbox.json")
    item = find(items, a.id)
    item.update(status="closed", closed=now(), answer=a.answer or item.get("answer", ""))
    save("inbox.json", items)
    print(f"inbox {a.id} closed")


# notes -------------------------------------------------------------------

def note_add(a):
    notes = load("notes.json")
    note = {"id": next_id(notes), "text": a.text, "kind": a.kind, "source": a.source,
            "valid_from": now(), "valid_to": None}
    notes.append(note)
    save("notes.json", notes)
    print(f"note {note['id']} added")


def note_list(a):
    notes = [n for n in load("notes.json") if a.all or n["valid_to"] is None]
    for n in notes:
        tail = "" if n["valid_to"] is None else f" (retired: {n.get('retired_reason', '')})"
        print(f"{n['id']}. [{n['kind']}] {n['text']} (source: {n['source']}, {n['valid_from'][:10]}){tail}")
    if not notes:
        print("no notes")


def note_retire(a):
    notes = load("notes.json")
    note = find(notes, a.id)
    note.update(valid_to=now(), retired_reason=a.reason)
    save("notes.json", notes)
    print(f"note {a.id} retired")


# tools -------------------------------------------------------------------

def content_hash(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    files = [path] if path.is_file() else sorted(
        p for p in path.rglob("*") if p.is_file() and not HASH_SKIP & set(p.relative_to(path).parts))
    for file in files:
        rel = file.name if path.is_file() else file.relative_to(path).as_posix()
        digest.update(rel.encode() + b"\0" + file.read_bytes() + b"\0")
    return digest.hexdigest()


def tool_pin(a):
    path = pathlib.Path(a.path).expanduser().resolve()
    if not path.exists():
        sys.exit(f"{path} does not exist")
    tools = load("tools.lock.json")
    digest = content_hash(path)
    old = next((t for t in tools if t["name"] == a.name), None)
    if old and old["sha256"] != digest and not a.force:
        sys.exit(f"{a.name} changed since it was pinned; re-vet it, then pin again with --force")
    tools = [t for t in tools if t["name"] != a.name]
    tools.append({"name": a.name, "path": str(path), "source": a.source or "", "sha256": digest, "pinned": now()})
    save("tools.lock.json", tools)
    print(f"pinned {a.name}")


def tool_check(a):
    drift = 0
    for t in load("tools.lock.json"):
        path = pathlib.Path(t["path"])
        if not path.exists():
            state = "MISSING"
        elif content_hash(path) != t["sha256"]:
            state = "CHANGED"
        else:
            state = "ok"
        drift += state != "ok"
        print(f"{t['name']}: {state}")
    if drift:
        sys.exit(f"{drift} tool(s) changed since pinned: re-vet before use")


def tool_list(a):
    tools = load("tools.lock.json")
    for t in tools:
        print(f"{t['name']}  {t['sha256'][:12]}  {t['source'] or t['path']}")
    if not tools:
        print("no pinned tools")


# overview ----------------------------------------------------------------

def status(a):
    root = home()
    open_goals = [g for g in load("goals.json") if g["status"] == "open"]
    items = load("inbox.json")
    inbox = [i for i in items if i["status"] == "open"]
    answered = sum(i["status"] == "answered" for i in items)
    counts = ", ".join(f"{k} {sum(i['kind'] == k for i in inbox)}" for k in INBOX_KINDS)
    if answered:
        counts += f" | answered {answered} (apply, then close)"
    runs = sorted(p for p in (root / "runs").iterdir() if p.is_dir())
    print("profile:", "yes" if (root / "profile.md").exists() else "missing, run onboarding")
    print(f"goals: {len(open_goals)} open | inbox: {counts}")
    if runs:
        nxt, total, _ = next_step(runs[-1])
        print(f"last run: {runs[-1].name} next: {('step ' + nxt) if nxt else 'done'}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sw", description="Stillwright state keeper")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=status)
    sub.add_parser("home").set_defaults(fn=lambda a: print(home()))

    goal = sub.add_parser("goal").add_subparsers(dest="sub", required=True)
    g = goal.add_parser("add"); g.add_argument("text"); g.add_argument("--priority", type=int, default=3, choices=range(1, 6)); g.set_defaults(fn=goal_add)
    g = goal.add_parser("list"); g.add_argument("--all", action="store_true"); g.set_defaults(fn=goal_list)
    g = goal.add_parser("done"); g.add_argument("id", type=int); g.add_argument("--note"); g.set_defaults(fn=goal_done)

    run = sub.add_parser("run").add_subparsers(dest="sub", required=True)
    r = run.add_parser("new"); r.add_argument("slug"); r.add_argument("--goal", type=int); r.set_defaults(fn=run_new)
    r = run.add_parser("log"); r.add_argument("run"); r.add_argument("pairs", nargs="+"); r.set_defaults(fn=run_log)
    r = run.add_parser("status"); r.add_argument("run", nargs="?", default="latest"); r.set_defaults(fn=run_status)
    run.add_parser("list").set_defaults(fn=run_list)

    inbox = sub.add_parser("inbox").add_subparsers(dest="sub", required=True)
    i = inbox.add_parser("add"); i.add_argument("kind", choices=INBOX_KINDS); i.add_argument("title"); i.add_argument("--body"); i.add_argument("--run"); i.set_defaults(fn=inbox_add)
    i = inbox.add_parser("list"); i.add_argument("--all", action="store_true"); i.set_defaults(fn=inbox_list)
    i = inbox.add_parser("show"); i.add_argument("id", type=int); i.set_defaults(fn=inbox_show)
    i = inbox.add_parser("answer"); i.add_argument("id", type=int); i.add_argument("answer"); i.set_defaults(fn=inbox_answer)
    i = inbox.add_parser("close"); i.add_argument("id", type=int); i.add_argument("--answer"); i.set_defaults(fn=inbox_close)

    note = sub.add_parser("note").add_subparsers(dest="sub", required=True)
    n = note.add_parser("add"); n.add_argument("text"); n.add_argument("--source", required=True); n.add_argument("--kind", choices=NOTE_KINDS, default="fact"); n.set_defaults(fn=note_add)
    n = note.add_parser("list"); n.add_argument("--all", action="store_true"); n.set_defaults(fn=note_list)
    n = note.add_parser("retire"); n.add_argument("id", type=int); n.add_argument("--reason", required=True); n.set_defaults(fn=note_retire)

    tool = sub.add_parser("tool").add_subparsers(dest="sub", required=True)
    t = tool.add_parser("pin"); t.add_argument("name"); t.add_argument("path"); t.add_argument("--source"); t.add_argument("--force", action="store_true"); t.set_defaults(fn=tool_pin)
    tool.add_parser("check").set_defaults(fn=tool_check)
    tool.add_parser("list").set_defaults(fn=tool_list)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    with locked():
        args.fn(args)


if __name__ == "__main__":
    main()
