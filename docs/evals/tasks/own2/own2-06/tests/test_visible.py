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
