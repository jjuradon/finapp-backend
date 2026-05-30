# app/modules/auth_household/utils/rate_limiter.py
import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis

from app.core.config import settings

# Global async redis client
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)


class RateLimiter:
    def __init__(self, redis=redis_client):
        self.redis = redis

    async def is_ip_rate_limited(self, ip: str) -> bool:
        """IP rate limiting: max 5 requests per minute per IP."""
        key = f"finapp:auth:rate:{ip}"
        val = await self.redis.incr(key)
        if val == 1:
            await self.redis.expire(key, 60)
        return val > 5

    async def is_user_locked(self, user_id: uuid.UUID) -> tuple[bool, str | None]:
        """Check if user account is locked. Returns (is_locked, locked_until_iso_str)."""
        key = f"finapp:auth:locked:{user_id}"
        val = await self.redis.get(key)
        if val:
            return True, val
        return False, None

    async def record_login_failure(self, user_id: uuid.UUID) -> tuple[bool, str | None]:
        """Record login failure. Returns (is_locked, locked_until_iso_str) if newly locked."""
        failures_key = f"finapp:auth:failures:{user_id}"
        lock_key = f"finapp:auth:locked:{user_id}"

        failures = await self.redis.incr(failures_key)
        if failures == 1:
            await self.redis.expire(failures_key, 900)  # 15 minutes window

        if failures >= 10:
            locked_until = datetime.now(UTC) + timedelta(minutes=15)
            locked_until_str = locked_until.isoformat()
            await self.redis.set(lock_key, locked_until_str, ex=900)
            return True, locked_until_str

        return False, None

    async def reset_failures(self, user_id: uuid.UUID) -> None:
        """Reset failures counter and lockout flag."""
        failures_key = f"finapp:auth:failures:{user_id}"
        lock_key = f"finapp:auth:locked:{user_id}"
        await self.redis.delete(failures_key, lock_key)
