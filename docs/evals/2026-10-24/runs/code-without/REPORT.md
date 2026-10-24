# Report

All 5 tests in `tests/` now pass (`python3 -m unittest discover -s tests`: Ran 5 tests, OK). I did not change the tests.

**Cause:** two tests failed (`test_flat5_never_negative` and `test_total_flat5_small_order`). In `apply_discount` in `pricing.py`, the `FLAT5` branch returned `subtotal - 5`. For a subtotal under 5 that goes negative: 3 gave -2, and a 2.00 order gave a total of -3.24. The function's own docstring already says FLAT5 "never [goes] below zero", so the code was wrong, not the tests.

**Fix:** one line in `pricing.py`:
`return subtotal - 5` became `return max(subtotal - 5, 0)`.

The second failing test needed no separate change. `order_total` calls `apply_discount`, so it now returns 0.0.

Nothing was pushed, published or installed.
