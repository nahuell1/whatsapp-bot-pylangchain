"""Lightweight event memory store for executed function calls.

Provides Redis-backed implementation with in-memory fallback.
"""
from __future__ import annotations

import logging
import datetime as dt
from abc import ABC, abstractmethod
from typing import List

try:  # pragma: no cover - optional dependency
    from redis.asyncio import Redis  # type: ignore
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore

logger = logging.getLogger(__name__)


class BaseMemoryStore(ABC):
    def __init__(self, max_events: int, ttl_days: int):
        self.max_events = max_events
        self.ttl_seconds = ttl_days * 86400 if ttl_days > 0 else None

    @abstractmethod
    async def add_event(self, user_id: str, line: str):
        ...

    @abstractmethod
    async def get_events(self, user_id: str, limit: int) -> List[str]:
        ...


class InMemoryMemoryStore(BaseMemoryStore):
    def __init__(self, max_events: int, ttl_days: int):
        super().__init__(max_events, ttl_days)
        self._data: dict[str, list[tuple[float, str]]] = {}

    async def add_event(self, user_id: str, line: str):
        now = dt.datetime.utcnow().timestamp()
        bucket = self._data.setdefault(user_id, [])
        bucket.insert(0, (now, line))
        # TTL purge
        if self.ttl_seconds:
            cutoff = now - self.ttl_seconds
            bucket[:] = [e for e in bucket if e[0] >= cutoff]
        # Trim
        if len(bucket) > self.max_events:
            del bucket[self.max_events:]

    async def get_events(self, user_id: str, limit: int) -> List[str]:
        return [line for _, line in self._data.get(user_id, [])[:limit]]


class RedisMemoryStore(BaseMemoryStore):  # pragma: no cover - network dependent
    def __init__(self, redis, max_events: int, ttl_days: int):
        super().__init__(max_events, ttl_days)
        self.redis = redis

    def _key(self, user_id: str) -> str:
        return f"bot:mem:{user_id}"

    async def add_event(self, user_id: str, line: str):
        key = self._key(user_id)
        pipe = self.redis.pipeline()
        pipe.lpush(key, line)
        pipe.ltrim(key, 0, self.max_events - 1)
        if self.ttl_seconds:
            pipe.expire(key, self.ttl_seconds)
        await pipe.execute()

    async def get_events(self, user_id: str, limit: int) -> List[str]:
        key = self._key(user_id)
        vals = await self.redis.lrange(key, 0, limit - 1)
        return [v.decode() if isinstance(v, bytes) else v for v in vals]


async def build_memory_store(settings) -> BaseMemoryStore | None:
    if not getattr(settings, 'MEMORY_ENABLED', True):
        logger.info("Memory disabled via settings")
        return None

    max_events = getattr(settings, 'MEMORY_MAX_EVENTS', 50)
    ttl_days = getattr(settings, 'MEMORY_TTL_DAYS', 7)

    if getattr(settings, 'REDIS_URL', None) and Redis is not None:
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
            if await redis.ping():
                logger.info(f"Using Redis memory store: {settings.REDIS_URL}")
                return RedisMemoryStore(redis, max_events, ttl_days)
        except Exception as e:
            logger.warning(f"Redis memory init failed, fallback to in-memory: {e}")

    logger.info("Using in-memory memory store")
    return InMemoryMemoryStore(max_events, ttl_days)
