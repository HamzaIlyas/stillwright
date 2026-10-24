import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pricing import apply_discount, order_total


class PricingTests(unittest.TestCase):
    def test_save10(self):
        self.assertEqual(apply_discount(100, "SAVE10"), 90)

    def test_flat5_never_negative(self):
        self.assertEqual(apply_discount(3, "FLAT5"), 0)

    def test_unknown_code(self):
        self.assertEqual(apply_discount(50, "NOPE"), 50)

    def test_total_with_tax(self):
        self.assertEqual(order_total([(10, 2), (5, 1)]), 27.0)

    def test_total_flat5_small_order(self):
        self.assertEqual(order_total([(2, 1)], "FLAT5"), 0.0)


if __name__ == "__main__":
    unittest.main()
