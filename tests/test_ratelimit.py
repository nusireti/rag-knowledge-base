"""限流器单元测试。"""

from app.ratelimit import RateLimitMiddleware, SlidingWindowLimiter


def test_allows_up_to_limit():
    limiter = SlidingWindowLimiter()
    for i in range(3):
        assert limiter.allow('k', 3, 60, now=1000.0 + i) is True
    assert limiter.allow('k', 3, 60, now=1003.0) is False


def test_window_slides():
    limiter = SlidingWindowLimiter()
    assert limiter.allow('k', 2, 60, now=1000.0) is True
    assert limiter.allow('k', 2, 60, now=1001.0) is True
    assert limiter.allow('k', 2, 60, now=1002.0) is False
    # 61 秒后第一条过期，名额恢复一个
    assert limiter.allow('k', 2, 60, now=1061.0) is True


def test_keys_are_independent():
    limiter = SlidingWindowLimiter()
    assert limiter.allow('a', 1, 60, now=0) is True
    assert limiter.allow('a', 1, 60, now=0) is False
    assert limiter.allow('b', 1, 60, now=0) is True


def test_zero_limit_means_unlimited():
    limiter = SlidingWindowLimiter()
    for _ in range(100):
        assert limiter.allow('k', 0) is True


def test_count_and_reset():
    limiter = SlidingWindowLimiter()
    limiter.allow('k', 10, 60, now=100.0)
    limiter.allow('k', 10, 60, now=101.0)
    assert limiter.count('k', 60, now=102.0) == 2
    limiter.reset()
    assert limiter.count('k', 60, now=102.0) == 0


def test_rule_matching():
    assert RateLimitMiddleware._rule_for('/api/auth/login')[0] == 'auth'
    assert RateLimitMiddleware._rule_for('/api/chat/ask')[0] == 'chat'
    assert RateLimitMiddleware._rule_for('/api/health') is None
    assert RateLimitMiddleware._rule_for('/api/knowledge-bases/') is None
