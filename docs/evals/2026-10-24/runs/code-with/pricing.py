"""Order pricing for a small shop."""
from typing import List, Optional, Tuple


def apply_discount(subtotal: float, code: Optional[str]) -> float:
    """Return the subtotal after the discount code, if any.

    SAVE10 takes 10% off. FLAT5 takes 5.00 off but never below zero.
    Unknown or empty codes change nothing.
    """
    if code == "SAVE10":
        return subtotal * 0.9
    if code == "FLAT5":
        return max(subtotal - 5, 0)
    return subtotal


def order_total(items: List[Tuple[float, int]], code: Optional[str] = None) -> float:
    """items are (unit_price, quantity). Discount applies to the subtotal, then 8% tax."""
    subtotal = sum(price * qty for price, qty in items)
    discounted = apply_discount(subtotal, code)
    return round(discounted * 1.08, 2)
