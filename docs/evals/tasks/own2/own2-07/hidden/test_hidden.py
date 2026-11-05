import pytest
from inventory import Inventory, OutOfStock


def test_reserve_takes_units_out():
    inv = Inventory({"pen": 10})
    rid = inv.reserve("pen", 4)
    assert isinstance(rid, str) and rid
    assert inv.available("pen") == 6


def test_out_of_stock_changes_nothing():
    inv = Inventory({"pen": 3})
    with pytest.raises(OutOfStock):
        inv.reserve("pen", 4)
    assert inv.available("pen") == 3
    with pytest.raises(OutOfStock):
        inv.reserve("unknown", 1)
    with pytest.raises(ValueError):
        inv.reserve("pen", 0)
    assert inv.available("pen") == 3


def test_release_is_idempotent_and_ids_are_unique():
    inv = Inventory({"pen": 5})
    a = inv.reserve("pen", 2)
    b = inv.reserve("pen", 2)
    assert a != b
    assert inv.available("pen") == 1
    inv.release(a)
    assert inv.available("pen") == 3
    inv.release(a)
    assert inv.available("pen") == 3
    with pytest.raises(KeyError):
        inv.release("nope")
    c = inv.reserve("pen", 3)
    assert c not in (a, b)
    assert inv.available("pen") == 0
