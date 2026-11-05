"""Second wrong fix: both methods evict, but remaining() keeps the old off-by-one at the window edge."""


class RateLimiter:
    def __init__(self, limit: int, window: float):
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window > 0")
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float) -> bool:
        hits = self._hits.setdefault(key, [])
        hits[:] = [t for t in hits if now - t < self.window]
        if len(hits) < self.limit:
            hits.append(now)
            return True
        return False

    def remaining(self, key: str, now: float) -> int:
        live = [t for t in self._hits.get(key, []) if now - t <= self.window]
        return max(0, self.limit - len(live))

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)
