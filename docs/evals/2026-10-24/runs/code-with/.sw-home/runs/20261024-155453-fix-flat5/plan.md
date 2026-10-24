# Goal: all tests in tests/ pass with tests/ unchanged.
1. Clamp FLAT5 result at zero in apply_discount (pricing.py only) | who: self (small edit) | check: python3 -m unittest discover -s tests exits 0 with 5 tests OK | after: -
2. Confirm tests untouched | who: self | check: md5 of tests/test_pricing.py equals the pre-work hash in .sw-home/tests.md5 | after: 1
Outward: none
