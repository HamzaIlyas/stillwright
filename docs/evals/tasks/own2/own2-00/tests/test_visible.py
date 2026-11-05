from wordfreq import counts, top_word


def test_punctuation_is_stripped():
    assert counts("The end. The END!") == {"the": 2, "end": 2}


def test_ties_go_alphabetically():
    assert top_word("pear apple") == "apple"
