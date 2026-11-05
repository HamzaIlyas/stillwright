from slugify import slugify


def test_accented_title_keeps_its_letters():
    assert slugify("Éclair au café") == "eclair-au-cafe"
