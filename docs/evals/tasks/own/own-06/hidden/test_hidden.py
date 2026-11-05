import pytest
from retry import TransientError, call_with_retry


def test_retries_until_success():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TransientError("not yet")
        return "ok"

    assert call_with_retry(flaky, attempts=5, backoff=0.01, sleep=lambda s: None) == "ok"
    assert len(calls) == 3


def test_backoff_doubles_and_never_sleeps_after_the_last_call():
    slept = []

    def always():
        raise TransientError("no")

    with pytest.raises(TransientError):
        call_with_retry(always, attempts=4, backoff=0.5, sleep=slept.append)
    assert slept == [0.5, 1.0, 2.0]


def test_other_exceptions_propagate_at_once():
    calls, slept = [], []

    def boom():
        calls.append(1)
        raise KeyError("fatal")

    with pytest.raises(KeyError):
        call_with_retry(boom, attempts=5, backoff=0.1, sleep=slept.append)
    assert calls == [1] and slept == []


def test_last_transient_error_is_reraised():
    n = {"i": 0}

    def numbered():
        n["i"] += 1
        raise TransientError(f"try {n['i']}")

    with pytest.raises(TransientError) as e:
        call_with_retry(numbered, attempts=3, backoff=0.1, sleep=lambda s: None)
    assert str(e.value) == "try 3"


def test_attempts_must_be_positive():
    with pytest.raises(ValueError):
        call_with_retry(lambda: 1, attempts=0, sleep=lambda s: None)
    assert call_with_retry(lambda: 7, attempts=1, sleep=lambda s: None) == 7
