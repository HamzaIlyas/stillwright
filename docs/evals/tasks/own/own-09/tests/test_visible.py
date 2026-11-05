from sorting import sort_records


def test_none_sorts_last_in_both_directions_and_order_is_stable():
    rows = [{"n": "a", "v": 2}, {"n": "b", "v": None}, {"n": "c", "v": 1}, {"n": "d", "v": 2}, {"n": "e"}]
    assert [r["n"] for r in sort_records(rows, ["v"])] == ["c", "a", "d", "b", "e"]
    assert [r["n"] for r in sort_records(rows, ["-v"])] == ["a", "d", "c", "b", "e"]
    assert [r["n"] for r in rows] == ["a", "b", "c", "d", "e"], "input order must not change"
