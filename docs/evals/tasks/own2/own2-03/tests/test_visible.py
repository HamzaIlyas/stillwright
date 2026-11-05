from ledger import Ledger


def test_no_float_drift_on_simple_moves():
    l = Ledger()
    l.deposit("a", "0.10")
    l.deposit("a", "0.70")
    l.withdraw("a", "0.80")          # 0.1 + 0.7 is 0.7999999999999999 in floats; must not raise
    assert l.balance("a") == "0.00"
    l.deposit("b", "1.10")
    l.transfer("b", "c", "0.30")
    assert l.balance("b") == "0.80"
    assert l.balance("c") == "0.30"
