All 5 tests in tests/ now pass, and I did not change the tests.

Cause: `apply_discount` in `pricing.py` returned `subtotal - 5` for FLAT5. Its own docstring says FLAT5 never goes below zero, so a small order came out negative. That broke two tests: `test_flat5_never_negative` (-2 instead of 0) and `test_total_flat5_small_order` (-3.24 instead of 0.0).

Fix: one line in `pricing.py`, `return max(subtotal - 5, 0)`. Nothing else changed.

Proof:
- Before the fix, `python3 -m unittest discover -s tests` showed 2 failures out of 5.
- After the fix it printed "Ran 5 tests ... OK" and exited 0.
- The md5 of `tests/test_pricing.py` was `ef09fb66a794a158278f12cfc0fd12da` before and after, so the tests are untouched.

I skipped onboarding as instructed, so no profile exists. The plan and the pass/fail log are in `.sw-home/runs/20261024-155453-fix-flat5/` (goal 1 is marked done). Nothing was pushed, published or installed.
