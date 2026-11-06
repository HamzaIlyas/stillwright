"""Cost per verified pass per arm with a cluster bootstrap over tasks (pilot 5 primary)."""
import unittest

from pilot_cost import cost_per_pass, ratio_ci


def rows(arm, per_task):
    out = []
    for task, (cost, verdict) in per_task.items():
        out.append({"task": task, "epoch": "1", "set": "set1", "verdict": verdict, "cost_usd": str(cost), "arm": arm})
    return out


class CostPerPassTests(unittest.TestCase):
    def test_cost_divides_all_cost_by_verified_passes_only(self):
        r = rows("plain", {"a": (1.0, "pass"), "b": (1.0, "false_done"), "c": (2.0, "void")})
        self.assertAlmostEqual(cost_per_pass(r), 4.0)   # 4.0 USD over 1 pass; void and false_done cost, do not count

    def test_no_passes_gives_infinity(self):
        self.assertEqual(cost_per_pass(rows("plain", {"a": (1.0, "false_done")})), float("inf"))

    def test_ratio_ci_is_one_when_arms_are_identical(self):
        r = rows("plain", {t: (1.0, "pass") for t in "abcdefghij"})
        lo, hi, point = ratio_ci(r, r, seed=1, b=200)
        self.assertEqual((lo, hi, point), (1.0, 1.0, 1.0))

    def test_no_passes_on_the_plain_side_is_undefined_not_zero(self):
        plain = rows("plain", {"a": (1.0, "false_done")})
        with_ = rows("with", {"a": (1.0, "pass")})
        self.assertEqual(ratio_ci(with_, plain, seed=1, b=20)[2], float("inf"))

    def test_both_arms_are_resampled_with_the_same_task_list(self):
        # per-task costs differ wildly across tasks but the with/plain ratio is 2 inside every task; a paired
        # resample keeps the ratio at exactly 2, an unpaired one would not
        plain = rows("plain", {t: (c, "pass") for t, c in zip("abcdefghij", [1, 50, 2, 90, 3, 70, 4, 60, 5, 80])})
        with_ = rows("with", {t: (2 * c, "pass") for t, c in zip("abcdefghij", [1, 50, 2, 90, 3, 70, 4, 60, 5, 80])})
        lo, hi, point = ratio_ci(with_, plain, seed=3, b=300)
        self.assertAlmostEqual(lo, 2.0); self.assertAlmostEqual(hi, 2.0); self.assertAlmostEqual(point, 2.0)

    def test_missing_cost_is_refused(self):
        with self.assertRaises(SystemExit):
            cost_per_pass([{"task": "a", "epoch": "1", "verdict": "pass", "cost_usd": ""}])

    def test_ratio_ci_brackets_a_real_difference(self):
        plain = rows("plain", {t: (1.0, "pass") for t in "abcdefghij"})
        with_ = rows("with", {t: (2.0, "pass") for t in "abcdefghij"})
        lo, hi, point = ratio_ci(with_, plain, seed=1, b=200)
        self.assertAlmostEqual(point, 2.0)
        self.assertTrue(lo <= 2.0 <= hi)


if __name__ == "__main__":
    unittest.main()
