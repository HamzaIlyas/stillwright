All 5 tests in `tests/` now pass. I ran `python3 -m unittest discover -s tests` before and after the fix.

**Cause:** `apply_discount` in `pricing.py` returned `subtotal - 5` for the `FLAT5` code. A small order went negative: 3 gave -2, and `order_total` gave -3.24. The function's docstring already said FLAT5 should never go below zero.

**Fix:** I changed that line to `return max(subtotal - 5, 0)`. I didn't touch the tests, and nothing was installed, pushed or published.

I didn't add any tests of my own, because the existing tests already cover the broken behaviour. I also didn't run the code-reviewer agent, since the change is a single line.
