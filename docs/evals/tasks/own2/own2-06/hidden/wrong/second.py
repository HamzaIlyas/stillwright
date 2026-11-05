"""Rules 1 and 3, but the backoff sleeps a constant and also sleeps after the last call."""
import time


class TransientError(Exception):
    """Raised by callers for failures that are worth retrying."""


def call_with_retry(fn, attempts: int = 3, backoff: float = 0.1, sleep=None):
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    sleep = sleep or time.sleep
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except TransientError as e:
            last = e
            sleep(backoff)
    raise last
