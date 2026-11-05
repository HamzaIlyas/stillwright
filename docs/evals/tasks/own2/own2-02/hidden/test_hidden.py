from slugify import slugify


def test_accented_title_keeps_its_letters():
    assert slugify("Éclair au café") == "eclair-au-cafe"
    assert slugify("Señor Ångström") == "senor-angstrom"


def test_runs_of_separators_collapse_to_one_dash():
    assert slugify("a --- b") == "a-b"
    assert slugify("one    two\tthree") == "one-two-three"
    assert slugify("x -- -- y") == "x-y"


def test_no_dash_at_the_ends():
    assert slugify("  --hello world!!  ") == "hello-world"
    assert slugify("--- ---") == ""


def test_respects_max_length_without_a_trailing_dash():
    s = slugify("the quick brown fox jumps", max_length=16)
    assert len(s) <= 16 and s and not s.endswith("-")
    assert s.startswith("the-quick")
    assert slugify("supercalifragilistic", max_length=5) == "super"
    assert len(slugify("a" * 100)) == 60
