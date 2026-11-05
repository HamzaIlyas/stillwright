from ratelimit import RateLimiter


def test_hit_expires_after_a_full_window():
    rl = RateLimiter(limit=3, window=10)
    assert rl.allow("c", 0)
    assert rl.allow("c", 1)
    assert rl.allow("c", 2)
    assert not rl.allow("c", 9)
    assert rl.allow("c", 10), "the hit at t=0 expired at t=10"
