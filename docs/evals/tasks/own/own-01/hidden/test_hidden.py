from ratelimit import RateLimiter


def test_hit_expires_after_a_full_window():
    rl = RateLimiter(limit=3, window=10)
    assert rl.allow("c", 0) and rl.allow("c", 1) and rl.allow("c", 2)
    assert not rl.allow("c", 9)
    assert rl.allow("c", 10)
    assert not rl.allow("c", 10.5)
    assert rl.allow("c", 11)


def test_remaining_after_a_quiet_window():
    rl = RateLimiter(limit=3, window=10)
    for t in (0, 1, 2):
        assert rl.allow("c", t)
    assert rl.remaining("c", 5) == 0
    assert rl.remaining("c", 10) == 1
    assert rl.remaining("c", 12) == 3
    assert rl.remaining("c", 60) == 3


def test_remaining_does_not_record_and_respects_the_edge():
    rl = RateLimiter(limit=2, window=5)
    assert rl.allow("c", 0)
    assert rl.remaining("c", 4.999) == 1
    assert rl.remaining("c", 5) == 2
    assert rl.allow("c", 5)
    assert rl.allow("c", 6)
    assert not rl.allow("c", 7)


def test_partial_use_then_idle_then_burst():
    rl = RateLimiter(limit=3, window=10)
    assert rl.allow("c", 0) and rl.allow("c", 1)
    assert rl.remaining("c", 50) == 3
    assert rl.allow("c", 50) and rl.allow("c", 51) and rl.allow("c", 52)
    assert not rl.allow("c", 53)
    assert rl.remaining("c", 53) == 0


def test_keys_are_independent_and_reset_works():
    rl = RateLimiter(limit=1, window=10)
    assert rl.allow("a", 0)
    assert rl.allow("b", 0)
    assert not rl.allow("a", 1)
    rl.reset("a")
    assert rl.allow("a", 1)
    assert rl.remaining("b", 1) == 0
