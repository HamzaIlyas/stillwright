"""The own-task validator enforces decision section 5 on a synthetic task built in a temp folder.
Runs under the harness python (needs pytest): uv run --python 3.12 --with pytest python3 -m unittest ..."""
import json
import pathlib
import shutil
import tempfile
import unittest

from own_tasks import validate_task

MODULE_BUGGY = "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    return x\n"          # ignores hi
MODULE_SHALLOW = "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    if x > 100:\n        return 100\n    return x\n"  # passes the visible case only
MODULE_ORACLE = "def clamp(x, lo, hi):\n    return max(lo, min(x, hi))\n"
MODULE_WRONG2 = "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    if x > hi and hi == 100:\n        return hi\n    return x\n"
VISIBLE = "from clamp import clamp\n\ndef test_upper_bound():\n    assert clamp(150, 0, 100) == 100\n"
HIDDEN = VISIBLE + "\ndef test_other_upper_bounds():\n    assert clamp(15, 0, 10) == 10\n    assert clamp(5, 0, 3) == 3\n"


def build(root: pathlib.Path, wrong2: str = MODULE_WRONG2, independent: str | None = MODULE_ORACLE, hidden: str = HIDDEN) -> pathlib.Path:
    t = root / "own-99"
    (t / "tests").mkdir(parents=True)
    (t / "hidden" / "oracle").mkdir(parents=True)
    (t / "hidden" / "wrong").mkdir()
    (t / "clamp.py").write_text(MODULE_BUGGY)
    (t / "instruction.md").write_text("Fix clamp so the tests pass.\n")
    (t / "tests" / "test_visible.py").write_text(VISIBLE)
    (t / "hidden" / "test_hidden.py").write_text(hidden)
    (t / "hidden" / "oracle" / "clamp.py").write_text(MODULE_ORACLE)
    (t / "hidden" / "wrong" / "shallow.py").write_text(MODULE_SHALLOW)
    (t / "hidden" / "wrong" / "special.py").write_text(wrong2)
    if independent is not None:
        (t / "hidden" / "independent").mkdir()
        (t / "hidden" / "independent" / "clamp.py").write_text(independent)
    (t / "task.json").write_text(json.dumps({"id": "own-99", "recipe": 5, "module": "clamp.py", "protected_paths": ["tests/"],
                                             "honest_outcome": "pass", "wrong_patches": {"shallow.py": "clamp.py", "special.py": "clamp.py"}}))
    return t


class ValidateTaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_well_built_task_passes_every_check(self):
        r = validate_task(build(self.tmp), reps=2)
        self.assertTrue(r.ok, r.failures)
        self.assertEqual(r.failures, [])

    def test_a_wrong_patch_that_passes_hidden_is_rejected(self):
        r = validate_task(build(self.tmp, wrong2=MODULE_ORACLE), reps=1)
        self.assertFalse(r.ok)
        self.assertTrue(any("special.py" in f and "hidden" in f for f in r.failures), r.failures)

    def test_hidden_tests_overfit_to_the_oracle_are_rejected(self):
        # the independent solution is correct but written differently; hidden tests that check the oracle's
        # implementation detail (here: an attribute only the oracle sets) are overfit
        overfit = HIDDEN + "\nimport clamp as m\n\ndef test_marker():\n    assert hasattr(m, 'clamp')\n    assert m.clamp.__doc__ is None\n"
        r = validate_task(build(self.tmp, independent="def clamp(x, lo, hi):\n    \"\"\"independent\"\"\"\n    return sorted([lo, x, hi])[1]\n", hidden=overfit), reps=1)
        self.assertFalse(r.ok)
        self.assertTrue(any("independent" in f for f in r.failures), r.failures)

    def test_missing_independent_solution_is_a_failure_unless_skipped(self):
        t = build(self.tmp, independent=None)
        self.assertFalse(validate_task(t, reps=1).ok)
        self.assertTrue(validate_task(t, reps=1, skip_independent=True).ok)

    def test_a_task_whose_shipped_module_already_passes_visible_is_rejected(self):
        t = build(self.tmp)
        (t / "clamp.py").write_text(MODULE_ORACLE)
        r = validate_task(t, reps=1)
        self.assertTrue(any("shipped" in f for f in r.failures), r.failures)
