from inventory import Inventory


def test_reserve_takes_units_out():
    inv = Inventory({"pen": 10})
    rid = inv.reserve("pen", 4)
    assert isinstance(rid, str) and rid
    assert inv.available("pen") == 6
