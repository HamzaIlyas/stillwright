import time


class TransientError(Exception):
    """Raised by callers for failures that are worth retrying."""


def call_with_retry(fn, attempts: int = 3, backoff: float = 0.1, sleep=None):
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    sleep = sleep or time.sleep
    wait = backoff
    last = None
    for i in range(attempts):
        try:
            return fn()
        except TransientError as e:
            last = e
            if i < attempts - 1:
                sleep(wait)
                wait *= 2
    raise last
