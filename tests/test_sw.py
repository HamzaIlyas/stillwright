"""Black-box tests for the sw binary. Set SW_BIN to test a specific build
(default: target/release/sw, then target/debug/sw)."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def find_binary() -> str:
    if os.environ.get("SW_BIN"):
        return os.environ["SW_BIN"]
    for build in ("release", "debug"):
        for name in ("sw", "sw.exe"):
            candidate = ROOT / "target" / build / name
            if candidate.exists():
                return str(candidate)
    raise SystemExit("sw binary not found: run `cargo build --release` or set SW_BIN")

SW = find_binary()

class Failed(Exception):
    pass

class SwTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = pathlib.Path(self.tmp.name)
        self.env = {**os.environ, "STILLWRIGHT_HOME": self.tmp.name}

    def sw(self, *argv, cwd=None):
        result = subprocess.run([SW, *argv], env=self.env, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            raise Failed(result.stderr.strip())
        return result.stdout

class GoalTests(SwTestCase):
    def test_add_list_done(self):
        self.sw("goal", "add", "Ship v0.1", "--priority", "1")
        self.sw("goal", "add", "Write launch post")
        listed = self.sw("goal", "list")
        self.assertLess(listed.index("Ship v0.1"), listed.index("Write launch post"))
        self.sw("goal", "done", "1")
        self.assertNotIn("Ship v0.1", self.sw("goal", "list"))
        self.assertIn("(done)", self.sw("goal", "list", "--all"))

    def test_unknown_id_exits(self):
        with self.assertRaises(Failed):
            self.sw("goal", "done", "99")

class RunTests(SwTestCase):
    def test_next_step_follows_plan_and_results(self):
        run = pathlib.Path(self.sw("run", "new", "Build Thing!").strip())
        self.assertTrue(run.name.endswith("-build-thing"))
        (run / "plan.md").write_text("# Goal: x\n1. a | check: true\n2. b | check: true\nOutward: none\n3. not a step\n")
        self.sw("run", "log", "latest", "step=1", "result=fail", "note=boom")
        self.assertIn("next: step 1", self.sw("run", "status"))
        self.sw("run", "log", "latest", "step=1", "result=pass")
        self.assertIn("next: step 2", self.sw("run", "status"))
        self.sw("run", "log", "latest", "step=2", "result=pass")
        self.assertIn("none, all passed", self.sw("run", "status"))

    def test_same_slug_same_second_gets_suffix(self):
        first = self.sw("run", "new", "dup").strip()
        second = self.sw("run", "new", "dup").strip()
        self.assertNotEqual(first, second)

    def test_corrupt_log_line_is_skipped(self):
        run = pathlib.Path(self.sw("run", "new", "x").strip())
        (run / "plan.md").write_text("1. a | check: true\n")
        (run / "log.jsonl").write_text("not json\n" + json.dumps({"step": "1", "result": "pass"}) + "\n")
        self.assertIn("none, all passed", self.sw("run", "status"))

    def test_log_refuses_folders_outside_runs(self):
        self.sw("run", "new", "x")
        outside = self.home / "notarun"
        outside.mkdir()
        with self.assertRaises(Failed):
            self.sw("run", "log", str(outside), "step=1", "result=pass")
        self.assertFalse((outside / "log.jsonl").exists())

    def test_run_reference_matches_slug_not_suffix(self):
        self.sw("run", "new", "alpha-1")
        self.sw("run", "new", "beta")
        self.assertIn("alpha-1", self.sw("run", "status", "alpha-1"))
        with self.assertRaises(Failed):
            self.sw("run", "status", "1")

    def test_bare_name_is_not_hijacked_by_cwd_folder(self):
        self.sw("run", "new", "x")
        (self.home / "x").mkdir()
        self.assertIn("-x:", self.sw("run", "status", "x", cwd=str(self.home)))

    def test_passed_counts_only_plan_steps(self):
        run = pathlib.Path(self.sw("run", "new", "x").strip())
        (run / "plan.md").write_text("1. a | check: true\n")
        self.sw("run", "log", "latest", "step=9", "result=pass")
        self.assertIn("0/1 steps passed", self.sw("run", "status"))

    def test_log_requires_key_value(self):
        self.sw("run", "new", "x")
        with self.assertRaises(Failed):
            self.sw("run", "log", "latest", "oops")

    def test_status_without_plan(self):
        self.sw("run", "new", "x")
        self.assertIn("write plan.md", self.sw("run", "status"))

class InboxTests(SwTestCase):
    def test_asks_sort_before_ideas_and_close(self):
        self.sw("inbox", "add", "idea", "Try a newsletter")
        self.sw("inbox", "add", "ask", "Which domain?")
        listed = self.sw("inbox", "list")
        self.assertLess(listed.index("Which domain?"), listed.index("Try a newsletter"))
        self.sw("inbox", "close", "2", "--answer", ".dev")
        self.assertNotIn("Which domain?", self.sw("inbox", "list"))
        saved = json.loads((self.home / "inbox.json").read_text())
        self.assertEqual(saved[1]["answer"], ".dev")

    def test_answer_stays_visible_until_closed(self):
        self.sw("inbox", "add", "review", "Publish v0.1?", "--body", "pushes to GitHub")
        self.assertIn("pushes to GitHub", self.sw("inbox", "show", "1"))
        self.sw("inbox", "answer", "1", "yes")
        self.assertIn("answered", self.sw("inbox", "list"))
        self.assertIn("answered 1", self.sw("status"))
        self.sw("inbox", "close", "1")
        self.assertIn("inbox empty", self.sw("inbox", "list"))
        self.assertIn("answer: yes", self.sw("inbox", "show", "1"))

    def test_closed_card_cannot_be_answered(self):
        self.sw("inbox", "add", "ask", "q")
        self.sw("inbox", "close", "1")
        with self.assertRaises(Failed):
            self.sw("inbox", "answer", "1", "late")

    def test_rejects_unknown_kind(self):
        with self.assertRaises(Failed):
            self.sw("inbox", "add", "spam", "nope")

class NoteTests(SwTestCase):
    def test_retired_notes_hidden_but_kept(self):
        self.sw("note", "add", "Prefers short replies", "--source", "chat 2026-10-16", "--kind", "preference")
        self.sw("note", "retire", "1", "--reason", "user changed mind")
        self.assertIn("no notes", self.sw("note", "list"))
        self.assertIn("retired: user changed mind", self.sw("note", "list", "--all"))

    def test_source_is_required(self):
        with self.assertRaises(Failed):
            self.sw("note", "add", "unsourced claim")

class ToolTests(SwTestCase):
    def hash_of(self, path):
        self.sw("tool", "pin", "h", str(path), "--force")
        return json.loads((self.home / "tools.lock.json").read_text())[0]["sha256"]

    def test_pin_then_detect_change_and_missing(self):
        tool = self.home / "some-skill"
        tool.mkdir()
        (tool / "SKILL.md").write_text("v1")
        self.sw("tool", "pin", "some-skill", str(tool), "--source", "https://example.com/x")
        self.assertIn("some-skill: ok", self.sw("tool", "check"))
        (tool / "SKILL.md").write_text("v2")
        with self.assertRaises(Failed):
            self.sw("tool", "check")
        (tool / "SKILL.md").unlink()
        tool.rmdir()
        with self.assertRaises(Failed):
            self.sw("tool", "check")

    def test_repin_of_changed_tool_needs_force(self):
        tool = self.home / "t.md"
        tool.write_text("v1")
        self.sw("tool", "pin", "t", str(tool))
        tool.write_text("v2")
        with self.assertRaises(Failed):
            self.sw("tool", "pin", "t", str(tool))
        self.sw("tool", "pin", "t", str(tool), "--force")
        self.assertIn("t: ok", self.sw("tool", "check"))

    def test_hash_covers_nested_dependency_dirs(self):
        tool = self.home / "c"
        (tool / "node_modules").mkdir(parents=True)
        (tool / "node_modules" / "m.js").write_text("v1")
        self.sw("tool", "pin", "c", str(tool))
        (tool / "node_modules" / "m.js").write_text("v2")
        with self.assertRaises(Failed):
            self.sw("tool", "check")

    def test_hash_ignores_regenerated_caches(self):
        tool = self.home / "c"
        tool.mkdir()
        (tool / "a.py").write_text("a")
        before = self.hash_of(tool)
        (tool / "__pycache__").mkdir()
        (tool / "__pycache__" / "a.pyc").write_bytes(b"x")
        (tool / ".DS_Store").write_bytes(b"x")
        self.assertEqual(before, self.hash_of(tool))

    @unittest.skipIf(os.name == "nt", "symlinks need privileges on Windows")
    def test_symlink_cycle_does_not_hang(self):
        tool = self.home / "s"
        (tool / "pkg").mkdir(parents=True)
        (tool / "pkg" / "loop").symlink_to(tool, target_is_directory=True)
        self.sw("tool", "pin", "s", str(tool))
        self.assertIn("s: ok", self.sw("tool", "check"))

    def test_hash_ignores_git_dir(self):
        tool = self.home / "t"
        (tool / ".git").mkdir(parents=True)
        (tool / "a.txt").write_text("a")
        before = self.hash_of(tool)
        (tool / ".git" / "HEAD").write_text("ref")
        self.assertEqual(before, self.hash_of(tool))

class CorruptStateTests(SwTestCase):
    def test_corrupt_json_gives_clear_error(self):
        (self.home / "goals.json").write_text("{broken")
        with self.assertRaises(Failed) as ctx:
            self.sw("status")
        self.assertIn("not valid JSON", str(ctx.exception))

class StatusTests(SwTestCase):
    def test_status_summarises(self):
        out = self.sw("status")
        self.assertIn("profile: missing", out)
        self.sw("run", "new", "x")
        self.assertIn("next: write plan.md", self.sw("status"))
        (self.home / "profile.md").write_text("# Profile")
        self.sw("goal", "add", "g")
        self.sw("inbox", "add", "ask", "q")
        out = self.sw("status")
        self.assertIn("profile: yes", out)
        self.assertIn("goals: 1 open", out)
        self.assertIn("ask 1", out)
        self.assertIn("top goal: 1. g", out)
        self.assertIn("needs you: 1. ask: q", out)
        self.sw("inbox", "add", "notify", "fyi")
        self.assertNotIn("fyi", self.sw("status"))

class InitTests(SwTestCase):
    def test_init_writes_both_settings_files(self):
        repo = self.home / "repo"
        repo.mkdir()
        out = self.sw("init", "--dir", str(repo))
        self.assertIn("Claude Code: updated", out)
        self.assertIn("GitHub Copilot: updated", out)
        for rel in (".claude/settings.json", ".github/copilot/settings.json"):
            data = json.loads((repo / rel).read_text())
            self.assertEqual(data["enabledPlugins"], {"stillwright@stillwright": True})
            self.assertEqual(data["extraKnownMarketplaces"]["stillwright"]["source"],
                             {"source": "github", "repo": "HamzaIlyas/stillwright"})

    def test_init_keeps_existing_keys_and_is_idempotent(self):
        repo = self.home / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".claude" / "settings.json").write_text(json.dumps({
            "permissions": {"allow": ["Bash(npm test)"]},
            "enabledPlugins": {"other@market": True},
        }))
        self.sw("init", "--dir", str(repo), "--claude-only")
        data = json.loads((repo / ".claude" / "settings.json").read_text())
        self.assertEqual(data["permissions"], {"allow": ["Bash(npm test)"]})
        self.assertEqual(data["enabledPlugins"], {"other@market": True, "stillwright@stillwright": True})
        self.assertFalse((repo / ".github").exists())
        self.assertIn("already set", self.sw("init", "--dir", str(repo), "--claude-only"))

    def test_init_refuses_broken_json_and_missing_dir(self):
        repo = self.home / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".claude" / "settings.json").write_text("{broken")
        with self.assertRaises(Failed):
            self.sw("init", "--dir", str(repo))
        with self.assertRaises(Failed):
            self.sw("init", "--dir", str(self.home / "nope"))

    def test_init_respects_opt_out_and_keeps_key_order(self):
        repo = self.home / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".claude" / "settings.json").write_text(
            '{"zeta": 1, "alpha": 2, "enabledPlugins": {"stillwright@stillwright": false}}')
        out = self.sw("init", "--dir", str(repo), "--claude-only")
        self.assertIn("left as is", out)
        text = (repo / ".claude" / "settings.json").read_text()
        self.assertIn('"stillwright@stillwright": false', text)
        self.assertLess(text.index("zeta"), text.index("alpha"))

    def test_init_handles_empty_file_and_rejects_non_object_plugins(self):
        repo = self.home / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".claude" / "settings.json").write_text("")
        self.sw("init", "--dir", str(repo), "--claude-only")
        self.assertIn("stillwright@stillwright", (repo / ".claude" / "settings.json").read_text())
        (repo / ".claude" / "settings.json").write_text('{"enabledPlugins": []}')
        with self.assertRaises(Failed):
            self.sw("init", "--dir", str(repo), "--claude-only")

    def test_init_strips_byte_order_mark(self):
        repo = self.home / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".claude" / "settings.json").write_text('\ufeff{"a": 1}', encoding="utf-8")
        self.sw("init", "--dir", str(repo), "--claude-only")
        data = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(data["a"], 1)
        self.assertIn("stillwright@stillwright", data["enabledPlugins"])

class CostTests(SwTestCase):
    def test_cost_sums_by_model_at_prices(self):
        (self.home / "prices.json").write_text(json.dumps({"small": {"in": 1.0, "out": 5.0}, "big": {"in": 3.0, "out": 15.0}}))
        self.sw("run", "new", "x")
        self.sw("run", "log", "latest", "step=1", "model=small", "in=1000000", "out=100000", "result=pass")
        self.sw("run", "log", "latest", "step=2", "model=big", "in=500000", "out=100000", "result=pass")
        self.sw("run", "log", "latest", "step=3", "model=small", "in=1000000", "out=0", "result=pass")
        out = self.sw("run", "cost")
        self.assertIn("small: in 2000000, out 100000, $2.5000", out)
        self.assertIn("big: in 500000, out 100000, $3.0000", out)
        self.assertIn("total: $5.5000", out)

    def test_cost_prices_dated_model_ids(self):
        (self.home / "prices.json").write_text(json.dumps({"claude-haiku-4-5": {"in": 1.0, "out": 5.0}}))
        self.sw("run", "new", "x")
        self.sw("run", "log", "latest", "step=1", "model=claude-haiku-4-5-20251001", "in=1000000", "out=0", "result=pass")
        self.assertIn("total: $1.0000", self.sw("run", "cost"))

    def test_cache_handles_odd_timestamps(self):
        p = self.home / "odd.jsonl"
        rows = []
        for i, created in enumerate((40000, 900, 40000)):
            rows.append(json.dumps({"type": "assistant", "timestamp": "2026-10-26T10:00:0" + "é" * 20,
                                    "message": {"id": f"m{i}", "model": "m", "usage": {"input_tokens": 2, "cache_creation_input_tokens": created, "cache_read_input_tokens": 40000 if i else 0, "output_tokens": 1}}}))
        p.write_text("\n".join(rows) + "\n")
        self.assertIn("3 turns", self.sw("cache", str(p)))

    def test_cost_fails_on_unpriced_model_and_handles_no_usage(self):
        self.sw("run", "new", "x")
        self.assertIn("no token usage logged", self.sw("run", "cost"))
        self.sw("run", "log", "latest", "step=1", "model=mystery", "in=10", "out=10")
        with self.assertRaises(Failed):
            self.sw("run", "cost")


class CacheTests(SwTestCase):
    def transcript(self, turns):
        lines = []
        for i, (model, inp, created, read, out) in enumerate(turns):
            msg = {"type": "assistant", "timestamp": f"2026-10-26T10:00:{i:02d}.000Z",
                   "message": {"id": f"m{i}", "model": model,
                               "usage": {"input_tokens": inp, "cache_creation_input_tokens": created,
                                         "cache_read_input_tokens": read, "output_tokens": out}}}
            lines.append(json.dumps(msg))
            lines.append(json.dumps(msg))  # duplicate block, must be counted once
        p = self.home / "session.jsonl"
        p.write_text("\n".join(lines) + "\n")
        return p

    def test_reports_model_switch_and_prefix_break(self):
        (self.home / "prices.json").write_text(json.dumps({"claude-sonnet-5-5": {"in": 2.0, "out": 10.0}}))
        p = self.transcript([
            ("claude-sonnet-5-5", 2, 40000, 0, 100),
            ("claude-sonnet-5-5", 2, 1000, 40000, 100),
            ("claude-opus-5-5", 2, 41000, 0, 100),
            ("claude-opus-5-5", 2, 500, 41000, 100),
            ("claude-opus-5-5", 2, 30000, 12000, 100),
        ])
        out = self.sw("cache", str(p))
        self.assertIn("5 turns", out)
        self.assertIn("model switched claude-sonnet-5-5 -> claude-opus-5-5", out)
        self.assertIn("prefix changed", out)
        self.assertIn("2 cache break(s)", out)
        self.assertIn("at most about $", out)

    def test_names_expired_cache_after_long_pause(self):
        p = self.transcript([("m", 2, 40000, 0, 50), ("m", 2, 800, 40000, 50)])
        late = {"type": "assistant", "timestamp": "2026-10-26T13:00:05.000Z",
                "message": {"id": "m9", "model": "m",
                            "usage": {"input_tokens": 2, "cache_creation_input_tokens": 40000,
                                      "cache_read_input_tokens": 0, "output_tokens": 50}}}
        p.write_text(p.read_text() + json.dumps(late) + "\n")
        out = self.sw("cache", str(p))
        self.assertIn("cache expired during a 180-minute pause", out)

    def test_clean_session_has_no_breaks(self):
        p = self.transcript([("m", 2, 40000, 0, 50), ("m", 2, 800, 40000, 50), ("m", 2, 900, 40800, 50)])
        out = self.sw("cache", str(p))
        self.assertIn("no cache breaks found", out)

    def test_rejects_file_without_usage(self):
        p = self.home / "x.jsonl"
        p.write_text('{"type":"user","message":{"content":"hi"}}\n')
        with self.assertRaises(Failed):
            self.sw("cache", str(p))


class CertificateTests(SwTestCase):
    """A step with a `$` check is done only with a receipt that is still fresh (mechanism 1)."""

    def setUp(self):
        super().setUp()
        self.work = pathlib.Path(self.tmp.name) / "work"
        self.work.mkdir()
        git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "init", "-q"], cwd=self.work, check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "init"], cwd=self.work, check=True)
        (self.work / "tests").mkdir()
        (self.work / "tests" / "t.sh").write_text("exit 0\n")
        self.run = pathlib.Path(self.sw("run", "new", "cert").strip())
        (self.run / "plan.md").write_text(
            "# Goal: x\n1. a | check: $ sh tests/t.sh\n2. b | check: reviewer reads it\nOutward: none\n"
        )

    def events(self):
        return [json.loads(l) for l in (self.run / "log.jsonl").read_text().splitlines() if l.strip()]

    def receipts(self, step="1"):
        return [e for e in self.events() if e.get("event") == "receipt" and e.get("step") == step]

    def test_check_runs_the_command_and_writes_a_receipt(self):
        out = self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("pass", out)
        receipt = self.receipts()[-1]
        self.assertEqual(receipt["cmd"], "sh tests/t.sh")
        self.assertEqual(receipt["exit"], 0)
        self.assertEqual(len(receipt["tree"]), 40)
        self.assertEqual(len(receipt["out_sha256"]), 64)
        logs = list((self.run / "checks").glob("1-*.log"))
        self.assertEqual(len(logs), 1)
        # a passing check is not yet "done": the step still needs sw run done
        self.assertIn("next: step 1", self.sw("run", "status"))

    def test_failing_check_is_logged_and_exits_nonzero(self):
        (self.work / "tests" / "t.sh").write_text("echo boom; exit 3\n")
        with self.assertRaises(Failed) as cm:
            self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("exit 3", str(cm.exception))
        self.assertEqual(self.receipts()[-1]["result"], "fail")
        self.assertIn("step 1: fail", self.sw("run", "status"))

    def test_a_failure_inside_a_pipe_fails_the_check(self):
        (self.run / "plan.md").write_text("# Goal: x\n1. a | check: $ false | cat\n")
        with self.assertRaises(Failed):
            self.sw("run", "check", "latest", "1", cwd=self.work)

    def test_pass_claim_without_a_receipt_is_refused(self):
        with self.assertRaises(Failed) as cm:
            self.sw("run", "log", "latest", "step=1", "result=pass")
        self.assertIn("sw run check", str(cm.exception))
        self.assertEqual(self.events(), [])
        # a step whose check is not a command may still be logged (reviewer path)
        self.sw("run", "log", "latest", "step=2", "result=pass")

    def test_done_needs_a_receipt_from_the_current_worktree(self):
        with self.assertRaises(Failed) as cm:
            self.sw("run", "done", "latest", "1", cwd=self.work)
        self.assertIn("no receipt", str(cm.exception))
        self.sw("run", "check", "latest", "1", cwd=self.work)
        (self.work / "new.txt").write_text("edited after the check\n")
        with self.assertRaises(Failed) as cm:
            self.sw("run", "done", "latest", "1", cwd=self.work)
        self.assertIn("stale", str(cm.exception))
        self.assertIn("next: step 1", self.sw("run", "status"))
        self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("certified", self.sw("run", "done", "latest", "1", cwd=self.work))
        done = self.events()[-1]
        self.assertEqual((done["step"], done["result"], done["certified"]), ("1", "pass", True))
        self.assertIn("next: step 2", self.sw("run", "status"))

    def test_done_refuses_a_failed_receipt(self):
        (self.work / "tests" / "t.sh").write_text("exit 1\n")
        with self.assertRaises(Failed):
            self.sw("run", "check", "latest", "1", cwd=self.work)
        with self.assertRaises(Failed) as cm:
            self.sw("run", "done", "latest", "1", cwd=self.work)
        self.assertIn("fail", str(cm.exception))

    def test_frozen_check_files_detect_tampering(self):
        self.sw("run", "freeze", "latest", "tests", cwd=self.work)
        frozen = os.path.realpath(self.work / "tests")
        self.assertEqual(list(self.events()[-1]["files"]), [frozen])
        self.sw("run", "check", "latest", "1", cwd=self.work)
        (self.work / "tests" / "t.sh").write_text("exit 0 # weakened\n")
        with self.assertRaises(Failed) as cm:
            self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("tamper", str(cm.exception))
        self.assertEqual(self.receipts()[-1]["tampered"], [frozen])
        self.assertEqual(self.receipts()[-1]["result"], "fail")
        with self.assertRaises(Failed):
            self.sw("run", "done", "latest", "1", cwd=self.work)
        # an explicit re-freeze is the only way on, and it stays in the log
        self.sw("run", "freeze", "latest", "tests", cwd=self.work)
        self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("certified", self.sw("run", "done", "latest", "1", cwd=self.work))

    def test_pipes_inside_a_check_are_kept(self):
        (self.run / "plan.md").write_text(
            "# Goal: x\n1. a | who: self | check: $ printf 'x\\ny\\n' | wc -l | grep -q 2 | after: -\n"
        )
        self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertEqual(self.receipts()[-1]["cmd"], "printf 'x\\ny\\n' | wc -l | grep -q 2")

    def test_duplicate_keys_in_log_are_refused(self):
        with self.assertRaises(Failed) as cm:
            self.sw("run", "log", "latest", "step=1", "result=fail", "result=pass")
        self.assertIn("duplicate", str(cm.exception))
        with self.assertRaises(Failed):
            self.sw("run", "log", "latest", "step=2", "step=1", "result=pass")
        self.assertEqual(self.events(), [])

    def test_done_refuses_when_the_plan_command_changed(self):
        self.sw("run", "check", "latest", "1", cwd=self.work)
        plan = (self.run / "plan.md").read_text().replace("$ sh tests/t.sh", "$ true")
        (self.run / "plan.md").write_text(plan)
        with self.assertRaises(Failed) as cm:
            self.sw("run", "done", "latest", "1", cwd=self.work)
        self.assertIn("plan", str(cm.exception))

    def test_prose_check_starting_with_a_dollar_sign_is_not_a_command(self):
        (self.run / "plan.md").write_text("# Goal: x\n1. a | check: $5 refund shown\n")
        with self.assertRaises(Failed) as cm:
            self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("not a command", str(cm.exception))
        self.sw("run", "log", "latest", "step=1", "result=pass")

    @unittest.skipIf(os.name == "nt" or os.geteuid() == 0, "needs a file git cannot read")
    def test_git_failure_inside_a_repo_is_an_error_not_a_pass(self):
        locked = self.work / "locked.txt"
        locked.write_text("x")
        locked.chmod(0)
        try:
            with self.assertRaises(Failed) as cm:
                self.sw("run", "check", "latest", "1", cwd=self.work)
            self.assertIn("git", str(cm.exception))
            self.assertEqual(self.receipts(), [])
        finally:
            locked.chmod(0o644)

    def test_state_folder_inside_the_repo_does_not_make_receipts_stale(self):
        self.env["STILLWRIGHT_HOME"] = str(self.work / ".swh")
        run = pathlib.Path(self.sw("run", "new", "inside").strip())
        (run / "plan.md").write_text("# Goal: x\n1. a | check: $ sh tests/t.sh\n")
        self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("certified", self.sw("run", "done", "latest", "1", cwd=self.work))

    def test_frozen_paths_are_absolute_so_the_directory_does_not_matter(self):
        self.sw("run", "freeze", "latest", "tests", cwd=self.work)
        sub = self.work / "sub"
        sub.mkdir()
        (self.run / "plan.md").write_text("# Goal: x\n1. a | check: $ sh ../tests/t.sh\n")
        self.sw("run", "check", "latest", "1", cwd=sub)
        (self.work / "tests" / "t.sh").write_text("exit 0 # changed\n")
        with self.assertRaises(Failed) as cm:
            self.sw("run", "check", "latest", "1", cwd=sub)
        self.assertIn("tamper", str(cm.exception))

    def test_done_also_detects_tampering(self):
        self.sw("run", "freeze", "latest", "tests", cwd=self.work)
        self.sw("run", "check", "latest", "1", cwd=self.work)
        (self.work / "tests" / "t.sh").write_text("exit 0 # after the check\n")
        with self.assertRaises(Failed) as cm:
            self.sw("run", "done", "latest", "1", cwd=self.work)
        self.assertIn("tamper", str(cm.exception))

    def test_check_writes_no_objects_into_the_repo(self):
        def objects():
            return subprocess.run(["git", "count-objects"], cwd=self.work, capture_output=True, text=True).stdout
        (self.work / "new.txt").write_text("new\n")
        before = objects()
        self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertEqual(objects(), before)

    @unittest.skipIf(os.name == "nt", "symlinks")
    def test_retargeting_a_frozen_symlink_is_tampering(self):
        (self.work / "real.sh").write_text("exit 0\n")
        (self.work / "weak.sh").write_text("exit 0 # weak\n")
        (self.work / "link.sh").symlink_to("real.sh")
        (self.run / "plan.md").write_text("# Goal: x\n1. a | check: $ sh link.sh\n")
        self.sw("run", "freeze", "latest", "link.sh", cwd=self.work)
        self.assertEqual(list(self.events()[-1]["files"]), [str(self.work.resolve() / "link.sh")])
        (self.work / "link.sh").unlink()
        (self.work / "link.sh").symlink_to("weak.sh")
        with self.assertRaises(Failed) as cm:
            self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertIn("tamper", str(cm.exception))

    def test_done_must_run_where_the_check_ran(self):
        self.sw("run", "check", "latest", "1", cwd=self.work)
        self.assertEqual(self.receipts()[-1]["cwd"], str(self.work.resolve()))
        sub = self.work / "sub"
        sub.mkdir()
        with self.assertRaises(Failed) as cm:
            self.sw("run", "done", "latest", "1", cwd=sub)
        self.assertIn("directory", str(cm.exception))

    def test_check_outside_git_still_works(self):
        plain = pathlib.Path(self.tmp.name) / "plain"
        plain.mkdir()
        (self.run / "plan.md").write_text("# Goal: x\n1. a | check: $ true\n")
        self.sw("run", "check", "latest", "1", cwd=plain)
        self.assertEqual(self.receipts()[-1]["tree"], "none")
        self.assertIn("certified", self.sw("run", "done", "latest", "1", cwd=plain))


class RewindTests(SwTestCase):
    """Every certified step leaves a snapshot; `sw run rewind` brings the files back (mechanism 2)."""

    def setUp(self):
        super().setUp()
        self.work = pathlib.Path(self.tmp.name) / "work"
        self.work.mkdir()
        self.git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*self.git, "init", "-q"], cwd=self.work, check=True)
        (self.work / ".gitignore").write_text("build/\n")
        (self.work / "a.txt").write_text("v1\n")
        (self.work / "tests").mkdir()
        (self.work / "tests" / "t.sh").write_text("exit 0\n")
        subprocess.run([*self.git, "add", "-A"], cwd=self.work, check=True)
        subprocess.run([*self.git, "commit", "-q", "-m", "init"], cwd=self.work, check=True)
        self.run = pathlib.Path(self.sw("run", "new", "rew").strip())
        (self.run / "plan.md").write_text("# Goal: x\n1. a | check: $ sh tests/t.sh\n2. b | check: $ true\n")

    def events(self):
        return [json.loads(l) for l in (self.run / "log.jsonl").read_text().splitlines() if l.strip()]

    def refs(self):
        out = subprocess.run(["git", "for-each-ref", "--format=%(refname)", "refs/sw/"],
                             cwd=self.work, capture_output=True, text=True, check=True).stdout
        return out.split()

    def tree_files(self, ref):
        out = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref],
                             cwd=self.work, capture_output=True, text=True, check=True).stdout
        return out.split()

    def certify(self, step):
        self.sw("run", "check", "latest", step, cwd=self.work)
        return self.sw("run", "done", "latest", step, cwd=self.work)

    def test_done_leaves_a_snapshot_of_the_tree(self):
        (self.work / "untracked.txt").write_text("kept\n")
        self.certify("1")
        done = self.events()[-1]
        self.assertEqual(len(done["snapshot"]), 40)
        self.assertEqual(self.refs(), [f"refs/sw/{self.run.name}/step-1"])
        self.assertIn("untracked.txt", self.tree_files(f"refs/sw/{self.run.name}/step-1"))

    def test_rewind_restores_the_step_and_keeps_what_it_removed(self):
        self.certify("1")
        (self.work / "a.txt").write_text("v2\n")
        (self.work / "junk.txt").write_text("later\n")
        (self.work / "tests" / "t.sh").unlink()
        (self.work / "build").mkdir()
        (self.work / "build" / "out.o").write_text("ignored\n")
        out = self.sw("run", "rewind", "latest", "1", cwd=self.work)
        self.assertIn("step 1", out)
        self.assertEqual((self.work / "a.txt").read_text(), "v1\n")
        self.assertFalse((self.work / "junk.txt").exists())
        self.assertEqual((self.work / "tests" / "t.sh").read_text(), "exit 0\n")
        self.assertTrue((self.work / "build" / "out.o").exists(), "ignored files are not touched")
        before = [r for r in self.refs() if "before-rewind" in r]
        self.assertEqual(len(before), 1)
        self.assertIn("junk.txt", self.tree_files(before[0]))
        self.assertEqual(self.events()[-1]["event"], "rewind")
        self.assertEqual(self.events()[-1]["step"], "1")

    def test_rewind_without_a_snapshot_is_refused(self):
        with self.assertRaises(Failed) as cm:
            self.sw("run", "rewind", "latest", "2", cwd=self.work)
        self.assertIn("no snapshot", str(cm.exception))

    def test_manual_snapshot_before_a_step(self):
        (self.work / "a.txt").write_text("v1b\n")
        out = self.sw("run", "snapshot", "latest", "2", cwd=self.work)
        self.assertIn("step 2", out)
        self.assertEqual(self.events()[-1]["event"], "snapshot")
        self.assertIn(f"refs/sw/{self.run.name}/step-2", self.refs())
        (self.work / "a.txt").write_text("broken\n")
        self.sw("run", "rewind", "latest", "2", cwd=self.work)
        self.assertEqual((self.work / "a.txt").read_text(), "v1b\n")

    def test_rewind_keeps_the_state_folder_inside_the_repo(self):
        self.env["STILLWRIGHT_HOME"] = str(self.work / ".swh")
        run = pathlib.Path(self.sw("run", "new", "inside").strip())
        (run / "plan.md").write_text("# Goal: x\n1. a | check: $ true\n")
        self.certify("1")
        (self.work / "junk.txt").write_text("x\n")
        self.sw("run", "rewind", "latest", "1", cwd=self.work)
        self.assertTrue((run / "plan.md").exists())
        self.assertFalse((self.work / "junk.txt").exists())
        self.assertIn('"rewind"', (run / "log.jsonl").read_text())

    def test_two_rewinds_in_a_row_keep_both_states(self):
        self.certify("1")
        (self.work / "precious.txt").write_text("keep me\n")
        self.sw("run", "rewind", "latest", "1", cwd=self.work)
        self.sw("run", "rewind", "latest", "1", cwd=self.work)
        kept = [r for r in self.refs() if "before-rewind" in r]
        self.assertEqual(len(kept), 2)
        self.assertTrue(any("precious.txt" in self.tree_files(r) for r in kept))

    def test_rewind_removes_files_with_non_ascii_names(self):
        self.certify("1")
        (self.work / "späce ü.txt").write_text("x\n")
        (self.work / "deep" / "er").mkdir(parents=True)
        (self.work / "deep" / "er" / "n.txt").write_text("x\n")
        self.sw("run", "rewind", "latest", "1", cwd=self.work)
        self.assertFalse((self.work / "späce ü.txt").exists())
        self.assertFalse((self.work / "deep").exists(), "emptied directories are removed too")

    def test_done_works_without_a_git_identity(self):
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["GIT_CONFIG_SYSTEM"] = os.devnull
        for key in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
            self.env.pop(key, None)
        self.assertIn("certified", self.certify("1"))

    def test_snapshot_outside_git_is_refused_but_done_still_works(self):
        plain = pathlib.Path(self.tmp.name) / "plain"
        plain.mkdir()
        with self.assertRaises(Failed) as cm:
            self.sw("run", "snapshot", "latest", "1", cwd=plain)
        self.assertIn("git", str(cm.exception))
        self.sw("run", "check", "latest", "2", cwd=plain)
        self.sw("run", "done", "latest", "2", cwd=plain)
        self.assertNotIn("snapshot", self.events()[-1])


if __name__ == "__main__":
    unittest.main()
