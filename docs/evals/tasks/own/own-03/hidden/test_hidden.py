import pytest
from ledger import Ledger


def test_no_float_drift_on_simple_moves():
    l = Ledger()
    l.deposit("a", "0.10")
    l.deposit("a", "0.70")
    l.withdraw("a", "0.80")
    assert l.balance("a") == "0.00"


def test_fee_rounds_half_up():
    l = Ledger()
    l.deposit("s", "100.00")
    l.transfer("s", "d", "1.00", fee_rate=0.015)   # fee 0.015 -> 0.02
    assert l.balance("fees") == "0.02"
    l.transfer("s", "d", "1.00", fee_rate=0.025)   # fee 0.025 -> 0.03
    assert l.balance("fees") == "0.05"
    l.transfer("s", "d", "1.00", fee_rate=0.0149)  # fee 0.0149 -> 0.01
    assert l.balance("fees") == "0.06"
    assert l.balance("s") == "96.94"
    assert l.balance("d") == "3.00"


def test_many_small_transfers_stay_exact():
    l = Ledger()
    l.deposit("s", "10.00")
    for _ in range(100):
        l.transfer("s", "d", "0.07", fee_rate=0.01)   # fee 0.0007 -> 0.00
    assert l.balance("s") == "3.00"
    assert l.balance("d") == "7.00"
    assert l.balance("fees") == "0.00"
    assert l.total() == "10.00"


def test_insufficient_funds_changes_nothing():
    l = Ledger()
    l.deposit("s", "1.00")
    with pytest.raises(ValueError):
        l.transfer("s", "d", "0.99", fee_rate=0.02)   # fee 0.0198 -> 0.02, needs 1.01
    assert l.balance("s") == "1.00"
    assert l.balance("d") == "0.00"
    assert l.balance("fees") == "0.00"
    with pytest.raises(ValueError):
        l.withdraw("s", "1.01")
    assert l.balance("s") == "1.00"


def test_total_and_unknown_accounts():
    l = Ledger()
    assert l.balance("nobody") == "0.00"
    assert l.total() == "0.00"
    l.deposit("a", 0.1)
    l.deposit("b", 0.2)
    assert l.total() == "0.30"
