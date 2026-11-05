import pytest
from sorting import sort_records


def test_none_sorts_last_in_both_directions_and_order_is_stable():
    rows = [{"n": "a", "v": 2}, {"n": "b", "v": None}, {"n": "c", "v": 1}, {"n": "d", "v": 2}, {"n": "e"}]
    assert [r["n"] for r in sort_records(rows, ["v"])] == ["c", "a", "d", "b", "e"]
    assert [r["n"] for r in sort_records(rows, ["-v"])] == ["a", "d", "c", "b", "e"]
    assert [r["n"] for r in rows] == ["a", "b", "c", "d", "e"]


def test_later_keys_break_ties():
    rows = [{"n": "a", "g": 1, "v": 5}, {"n": "b", "g": 2, "v": 9}, {"n": "c", "g": 1, "v": 7}, {"n": "d", "g": 2, "v": None}]
    assert [r["n"] for r in sort_records(rows, ["g", "-v"])] == ["c", "a", "b", "d"]
    assert [r["n"] for r in sort_records(rows, ["-g", "v"])] == ["b", "d", "a", "c"]


def test_unknown_key_raises_with_the_exact_message():
    with pytest.raises(KeyError) as e:
        sort_records([{"a": 1}], ["zzz"])
    assert e.value.args[0] == "unknown sort key: zzz"
    

def test_strings_and_mixed_none():
    rows = [{"s": "pear"}, {"s": None}, {"s": "apple"}, {"s": "fig"}]
    assert [r["s"] for r in sort_records(rows, ["-s"])] == ["pear", "fig", "apple", None]
