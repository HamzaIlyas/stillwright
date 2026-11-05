"""A sliding-window rate limiter: at most `limit` hits per key within any `window` seconds.
`allow(key, now)` records the hit when it is permitted; `remaining(key, now)` tells how many hits a key
has left at `now`; `reset(key)` forgets a key. `now` is a number of seconds supplied by the caller."""


class RateLimiter:
    def __init__(self, limit: int, window: float):
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window > 0")
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = {}

    def _live(self, key: str, now: float) -> list[float]:
        hits = [t for t in self._hits.get(key, []) if now - t < self.window]
        self._hits[key] = hits
        return hits

    def allow(self, key: str, now: float) -> bool:
        hits = self._live(key, now)
        if len(hits) < self.limit:
            hits.append(now)
            return True
        return False

    def remaining(self, key: str, now: float) -> int:
        return max(0, self.limit - len(self._live(key, now)))

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)
