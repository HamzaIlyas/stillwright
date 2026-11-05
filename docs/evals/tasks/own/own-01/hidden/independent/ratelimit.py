"""A sliding-window rate limiter.

Contract:
- `allow(key, now)` returns True and records the hit when fewer than `limit` hits for `key` are live at
  time `now`; otherwise returns False and records nothing.
- A hit made at time `t` is live at time `now` while `now - t < window`. At `now == t + window` it has
  expired.
- `remaining(key, now)` is `limit` minus the number of live hits for `key` at `now`; it never records
  anything and never goes below 0.
- Keys are independent. `now` is a monotonic number of seconds supplied by the caller.
"""


class RateLimiter:
    def __init__(self, limit: int, window: float):
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window > 0")
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = {}

    def _live(self, key: str, now: float) -> list[float]:
        return [t for t in self._hits.get(key, []) if now - t < self.window]

    def allow(self, key: str, now: float) -> bool:
        hits = self._live(key, now)
        if len(hits) < self.limit:
            self._hits[key] = [*hits, now]
            return True
        self._hits[key] = hits
        return False

    def remaining(self, key: str, now: float) -> int:
        return max(0, self.limit - len(self._live(key, now)))

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)
