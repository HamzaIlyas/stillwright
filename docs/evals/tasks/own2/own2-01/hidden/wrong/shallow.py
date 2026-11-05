"""Shallow fix: only the comparison in allow() is corrected; remaining() still never evicts."""


class RateLimiter:
    def __init__(self, limit: int, window: float):
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window > 0")
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float) -> bool:
        hits = self._hits.setdefault(key, [])
        if len(hits) >= self.limit:
            hits[:] = [t for t in hits if now - t < self.window]
        if len(hits) < self.limit:
            hits.append(now)
            return True
        return False

    def remaining(self, key: str, now: float) -> int:
        hits = self._hits.get(key, [])
        return max(0, self.limit - len(hits))

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)
