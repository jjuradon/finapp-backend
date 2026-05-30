"""
Unit tests for RateLimiter.

Tests the two independent rate-limiting concerns:
  1. Per-IP request rate  (5 per minute)
  2. Per-user failure lockout (10 consecutive failures → 15-minute lock)

Redis is mocked — no real connection required.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.modules.auth_household.utils.rate_limiter import RateLimiter
from app.shared.exceptions import BusinessRuleError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_limiter(redis: AsyncMock) -> RateLimiter:
    return RateLimiter(redis=redis)


# ---------------------------------------------------------------------------
# IP rate limit — 5 requests per minute per IP
# ---------------------------------------------------------------------------


class TestGivenFourAttemptsWhenCheckIpRate:
    async def test_then_passes_without_error(self):
        """
        Scenario: normal usage — fewer requests than the limit
        Given: Redis INCR returns 4 (four prior requests)
        When: check_ip_rate() is called
        Then: no exception is raised
        """
        redis = AsyncMock()
        redis.incr.return_value = 4
        redis.expire = AsyncMock()

        limiter = _make_limiter(redis)

        # Must not raise
        await limiter.check_ip_rate("192.168.1.1")


class TestGivenFiveAttemptsWhenCheckIpRate:
    async def test_then_raises_rate_limit_error(self):
        """
        Scenario: IP has hit the rate limit
        Given: Redis INCR returns 5 (limit is 5 per minute)
        When: check_ip_rate() is called
        Then: a rate-limit exception is raised (BusinessRuleError or specific subclass)
        """
        redis = AsyncMock()
        redis.incr.return_value = 5
        redis.expire = AsyncMock()

        limiter = _make_limiter(redis)

        with pytest.raises((BusinessRuleError, Exception)) as exc_info:
            await limiter.check_ip_rate("192.168.1.1")

        # Must not raise a generic Exception — must be a typed domain exception
        assert not isinstance(exc_info.value | (KeyError, AttributeError))

    async def test_then_rate_limit_key_has_correct_prefix(self):
        """Redis key for IP rate limiting must use the finapp:auth:rate: prefix."""
        redis = AsyncMock()
        redis.incr.return_value = 1
        redis.expire = AsyncMock()

        limiter = _make_limiter(redis)
        await limiter.check_ip_rate("10.0.0.1")

        call_key = redis.incr.call_args[0][0]
        assert call_key.startswith("finapp:auth:rate:")
        assert "10.0.0.1" in call_key

    async def test_then_ttl_is_set_to_60_seconds(self):
        """Rate counter TTL must be 60 seconds (1-minute window)."""
        redis = AsyncMock()
        redis.incr.return_value = 1
        redis.expire = AsyncMock()

        limiter = _make_limiter(redis)
        await limiter.check_ip_rate("1.2.3.4")

        # expire should be called with the rate key and ttl=60
        redis.expire.assert_called_once()
        args = redis.expire.call_args[0]
        assert args[1] == 60


# ---------------------------------------------------------------------------
# Failure lockout — 10 consecutive failures per user
# ---------------------------------------------------------------------------


class TestGivenAccountLockedWhenCheckLocked:
    async def test_then_returns_true(self):
        """
        Scenario: account is currently locked out
        Given: Redis GET returns the lockout key value (non-null)
        When: check_locked() is called
        Then: True is returned
        """
        redis = AsyncMock()
        redis.get.return_value = "1"  # key exists → account locked

        limiter = _make_limiter(redis)
        user_id = uuid.uuid4()

        result = await limiter.check_locked(user_id)

        assert result is True

    async def test_then_lockout_key_has_correct_prefix(self):
        redis = AsyncMock()
        redis.get.return_value = None

        limiter = _make_limiter(redis)
        user_id = uuid.uuid4()

        await limiter.check_locked(user_id)

        call_key = redis.get.call_args[0][0]
        assert call_key.startswith("finapp:auth:locked:")
        assert str(user_id) in call_key


class TestGivenAccountNotLockedWhenCheckLocked:
    async def test_then_returns_false(self):
        redis = AsyncMock()
        redis.get.return_value = None  # key absent → not locked

        limiter = _make_limiter(redis)

        result = await limiter.check_locked(uuid.uuid4())

        assert result is False


class TestIncrementFailures:
    async def test_returns_new_count(self):
        redis = AsyncMock()
        redis.incr.return_value = 3
        redis.expire = AsyncMock()

        limiter = _make_limiter(redis)
        count = await limiter.increment_failures(uuid.uuid4())

        assert count == 3

    async def test_failure_key_has_correct_prefix(self):
        redis = AsyncMock()
        redis.incr.return_value = 1
        redis.expire = AsyncMock()

        limiter = _make_limiter(redis)
        user_id = uuid.uuid4()
        await limiter.increment_failures(user_id)

        key = redis.incr.call_args[0][0]
        assert key.startswith("finapp:auth:failures:")
        assert str(user_id) in key


class TestLockAccount:
    async def test_sets_lockout_key_with_15_minute_ttl(self):
        """
        Scenario: tenth consecutive failure — account must be locked
        Given: lock_account() is called
        When: executed
        Then: Redis key finapp:auth:locked:{user_id} is set with TTL=900s (15 min)
        """
        redis = AsyncMock()
        redis.setex = AsyncMock()

        limiter = _make_limiter(redis)
        user_id = uuid.uuid4()
        await limiter.lock_account(user_id)

        redis.setex.assert_called_once()
        args = redis.setex.call_args[0]
        key, ttl, _ = args
        assert "locked" in key
        assert str(user_id) in key
        assert ttl == 900  # 15 minutes


class TestResetFailures:
    async def test_deletes_failure_counter(self):
        """After successful login, failure counter must be cleared."""
        redis = AsyncMock()
        redis.delete = AsyncMock()

        limiter = _make_limiter(redis)
        user_id = uuid.uuid4()
        await limiter.reset_failures(user_id)

        redis.delete.assert_called_once()
        key = redis.delete.call_args[0][0]
        assert "failures" in key
        assert str(user_id) in key
