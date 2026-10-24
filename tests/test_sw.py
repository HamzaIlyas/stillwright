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

    def sw(self, *argv):
        result = subprocess.run([SW, *argv], env=self.env, capture_output=True, text=True)
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

    def test_hash_ignores_caches(self):
        tool = self.home / "c"
        tool.mkdir()
        (tool / "a.py").write_text("a")
        before = self.hash_of(tool)
        (tool / "__pycache__").mkdir()
        (tool / "__pycache__" / "a.pyc").write_bytes(b"x")
        (tool / ".DS_Store").write_bytes(b"x")
        self.assertEqual(before, self.hash_of(tool))

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
        (self.home / "profile.md").write_text("# Profile")
        self.sw("goal", "add", "g")
        self.sw("inbox", "add", "ask", "q")
        out = self.sw("status")
        self.assertIn("profile: yes", out)
        self.assertIn("goals: 1 open", out)
        self.assertIn("ask 1", out)


if __name__ == "__main__":
    unittest.main()
