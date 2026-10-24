# Goal: all tests in tests/ pass with tests/ unchanged.
1. Clamp FLAT5 discount at zero in pricing.py apply_discount | who: self | check: cd code-with && python3 -m unittest discover -s tests exits 0 | after: -
2. Confirm tests/ unmodified | who: self | check: shasum of tests/test_pricing.py equals the hash taken before the edit | after: 1
Outward: none
