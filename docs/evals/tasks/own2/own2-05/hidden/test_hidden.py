from csvclean import clean


def test_trims_every_cell():
    rows = [{"name": "  Ada Lovelace ", "email": " ada@example.com", "phone": " "}]
    out = clean(rows)
    assert out[0]["name"] == "Ada Lovelace"
    assert out[0]["email"] == "ada@example.com"
    assert out[0]["phone"] == ""
    assert rows[0]["name"] == "  Ada Lovelace "


def test_phone_is_digits_with_a_plus():
    out = clean([{"name": "A", "email": "a@x.io", "phone": "(0049) 30 / 123-456"},
                 {"name": "B", "email": "b@x.io", "phone": "+1 555 0100"},
                 {"name": "C", "email": "c@x.io", "phone": ""}])
    assert [r["phone"] for r in out] == ["+004930123456", "+15550100", ""]


def test_duplicates_by_email_case_insensitively_keep_the_first():
    out = clean([{"name": "First", "email": "Ada@Example.com", "phone": "1"},
                 {"name": "Second", "email": "ada@example.com ", "phone": "2"},
                 {"name": "Other", "email": "bob@example.com", "phone": "3"},
                 {"name": "Third", "email": " ADA@EXAMPLE.COM", "phone": "4"}])
    assert [r["name"] for r in out] == ["First", "Other"]
    assert out[0]["phone"] == "+1"


def test_returns_new_objects():
    rows = [{"name": "A", "email": "a@x.io", "phone": "12"}]
    out = clean(rows)
    assert out is not rows and out[0] is not rows[0]
