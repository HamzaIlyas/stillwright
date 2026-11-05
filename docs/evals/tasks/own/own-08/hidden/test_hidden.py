import pytest
from duration import parse_duration


@pytest.mark.parametrize("text,seconds", [
    ("1h30m15s", 5415), ("90m", 5400), ("2h", 7200), ("45s", 45), ("1h 5s", 3605),
    ("1h 30m 15s", 5415), (" 45s ", 45), ("0s", 0), ("0h0m0s", 0), ("100h", 360000), ("1h  5s", 3605),
])
def test_accepted(text, seconds):
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["", "   ", "1x", "1h1h", "1m2h", "15", "-1s", "1.5h", "h", "1h30m15s2s",
                                  "1s1m", "+1h", "1h,5s", "1 h", "1H"])
def test_rejected_with_the_exact_message(text):
    with pytest.raises(ValueError) as e:
        parse_duration(text)
    assert str(e.value) == "invalid duration: " + text
    assert type(e.value) is ValueError
