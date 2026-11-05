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
        """Hits still inside the window at `now` (a hit expires once a full window has passed)."""
        return [t for t in self._hits.get(key, []) if now - t < self.window]

    def allow(self, key: str, now: float) -> bool:
        hits = self._live(key, now)
        allowed = len(hits) < self.limit
        if allowed:
            hits.append(now)
        if hits:
            self._hits[key] = hits
        else:
            self._hits.pop(key, None)
        return allowed

    def remaining(self, key: str, now: float) -> int:
        return max(0, self.limit - len(self._live(key, now)))

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)
