Tests pass: FLAT5 now clamps at zero.
Fixed `apply_discount` in pricing.py: `return max(subtotal - 5, 0)`.
Proof: `python3 -m unittest discover -s tests` ran 5 tests, OK (it was 2 failures before).
tests/ unchanged (hash matches the one taken before the edit).
