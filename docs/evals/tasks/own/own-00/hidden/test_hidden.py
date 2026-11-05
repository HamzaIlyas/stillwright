from wordfreq import counts, top_word


def test_punctuation_is_stripped():
    assert counts("The end. The END!") == {"the": 2, "end": 2}
    assert counts("'quoted' word; word:") == {"quoted": 1, "word": 2}


def test_ties_go_alphabetically():
    assert top_word("pear apple") == "apple"
    assert top_word("pear apple fig kiwi") == "apple"
    assert top_word("b b a a c") == "a"
    assert top_word("") is None
