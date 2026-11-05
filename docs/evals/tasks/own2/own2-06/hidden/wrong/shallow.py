"""Rule 1 only: retries, no backoff sleep, and a bare except that also retries fatal errors."""


class TransientError(Exception):
    """Raised by callers for failures that are worth retrying."""


def call_with_retry(fn, attempts: int = 3, backoff: float = 0.1, sleep=None):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last
