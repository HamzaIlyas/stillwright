"""Retry helper."""

import time


class TransientError(Exception):
    """Raised by callers for failures that are worth retrying."""


def call_with_retry(fn, attempts: int = 3, backoff: float = 0.1, sleep=None):
    """Call fn(), retrying on TransientError up to `attempts` calls in total.

    Waits backoff, 2*backoff, ... via sleep(seconds) between calls (none after
    the last). Other exceptions propagate immediately; the last TransientError
    is re-raised when every attempt fails.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
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
