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


def test_cut_at_a_word_boundary():
    assert slugify("the quick brown fox jumps", max_length=15) == "the-quick-brown"
    assert slugify("the quick brown fox jumps", max_length=14) == "the-quick"
    assert slugify("the quick brown fox jumps", max_length=9) == "the-quick"
    assert slugify("supercalifragilistic", max_length=5) == "super"


def test_unreducible_characters_are_dropped():
    assert slugify("Smørrebrød") == "smrrebrd"
    assert slugify("日本語") == ""
