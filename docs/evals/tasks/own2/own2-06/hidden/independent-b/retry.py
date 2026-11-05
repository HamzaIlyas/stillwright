"""Retry helper."""

import time


class TransientError(Exception):
    """Raised by callers for failures that are worth retrying."""


def call_with_retry(fn, attempts: int = 3, backoff: float = 0.1, sleep=None):
    """Call fn(), retrying on TransientError up to `attempts` calls in total.

    Waits via sleep(seconds) between calls, starting at `backoff` and doubling;
    no wait after the last call. Other exceptions propagate immediately; the
    last TransientError is re-raised when all attempts fail.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if sleep is None:
        sleep = time.sleep
    delay = backoff
    for attempt in range(attempts):
        try:
            return fn()
        except TransientError:
            if attempt == attempts - 1:
                raise
        sleep(delay)
        delay *= 2
