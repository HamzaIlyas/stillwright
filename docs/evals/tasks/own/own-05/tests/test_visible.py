from csvclean import clean


def test_trims_every_cell():
    rows = [{"name": "  Ada Lovelace ", "email": " ada@example.com", "phone": "+44 20 7946 0000 "}]
    out = clean(rows)
    assert out[0]["name"] == "Ada Lovelace"
    assert out[0]["email"] == "ada@example.com"
    assert out[0]["phone"].strip() == out[0]["phone"]
    assert rows[0]["name"] == "  Ada Lovelace ", "input must not be modified"
