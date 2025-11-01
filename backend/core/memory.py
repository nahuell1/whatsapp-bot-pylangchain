"""Lightweight event memory store for executed function calls.

Provides Redis-backed implementation with in-memory fallback for
storing and retrieving user interaction history.
"""

from __future__ import annotations

import datetime as dt
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore

logger = logging.getLogger(__name__)

SECONDS_PER_DAY = 86400


class BaseMemoryStore(ABC):
    """Abstract base class for memory storage implementations.
    
    Attributes:
        max_events: Maximum number of events to store per user
        ttl_seconds: Time-to-live in seconds for stored events
    """
    
    def __init__(self, max_events: int, ttl_days: int):
        """Initialize the memory store.
        
        Args:
            max_events: Maximum events to store per user
            ttl_days: Days to keep events before expiration
        """
        self.max_events = max_events
        self.ttl_seconds = (
            ttl_days * SECONDS_PER_DAY if ttl_days > 0 else None
        )

    @abstractmethod
    async def add_event(self, user_id: str, line: str) -> None:
        """Add an event to user's history.
        
        Args:
            user_id: User identifier
            line: Event description to store
        """
        ...

    @abstractmethod
    async def get_events(self, user_id: str, limit: int) -> List[str]:
        """Retrieve recent events for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of events to retrieve
            
        Returns:
            List of event descriptions, most recent first
        """
        ...


class InMemoryMemoryStore(BaseMemoryStore):
    """In-memory implementation of memory store.
    
    Stores events in memory with automatic TTL-based cleanup.
    Suitable for development or single-instance deployments.
    
    Attributes:
        _data: Dictionary mapping user IDs to event lists with timestamps
    """
    
    def __init__(self, max_events: int, ttl_days: int):
        """Initialize in-memory store.
        
        Args:
            max_events: Maximum events to store per user
            ttl_days: Days to keep events before expiration
        """
        super().__init__(max_events, ttl_days)
        self._data: dict[str, list[tuple[float, str]]] = {}

    async def add_event(self, user_id: str, line: str) -> None:
        """Add event to in-memory storage with TTL cleanup.
        
        Args:
            user_id: User identifier
            line: Event description to store
        """
        now = dt.datetime.utcnow().timestamp()
        bucket = self._data.setdefault(user_id, [])
        bucket.insert(0, (now, line))
        
        if self.ttl_seconds:
            cutoff = now - self.ttl_seconds
            bucket[:] = [e for e in bucket if e[0] >= cutoff]
        
        if len(bucket) > self.max_events:
            del bucket[self.max_events:]

    async def get_events(self, user_id: str, limit: int) -> List[str]:
        """Retrieve events from in-memory storage.
        
        Args:
            user_id: User identifier
            limit: Maximum number of events to retrieve
            
        Returns:
            List of event descriptions, most recent first
        """
        return [line for _, line in self._data.get(user_id, [])[:limit]]


class RedisMemoryStore(BaseMemoryStore):  # pragma: no cover
    """Redis-backed implementation of memory store.
    
    Provides persistent, distributed storage suitable for
    production deployments with multiple instances.
    
    Attributes:
        redis: Redis client instance
    """
    
    def __init__(self, redis, max_events: int, ttl_days: int):
        """Initialize Redis-backed store.
        
        Args:
            redis: Redis client instance
            max_events: Maximum events to store per user
            ttl_days: Days to keep events before expiration
        """
        super().__init__(max_events, ttl_days)
        self.redis = redis

    def _key(self, user_id: str) -> str:
        """Generate Redis key for user's event list.
        
        Args:
            user_id: User identifier
            
        Returns:
            Redis key string
        """
        return f"bot:mem:{user_id}"

    async def add_event(self, user_id: str, line: str) -> None:
        """Add event to Redis storage with TTL.
        
        Args:
            user_id: User identifier
            line: Event description to store
        """
        key = self._key(user_id)
        pipe = self.redis.pipeline()
        pipe.lpush(key, line)
        pipe.ltrim(key, 0, self.max_events - 1)
        if self.ttl_seconds:
            pipe.expire(key, self.ttl_seconds)
        await pipe.execute()

    async def get_events(self, user_id: str, limit: int) -> List[str]:
        """Retrieve events from Redis storage.
        
        Args:
            user_id: User identifier
            limit: Maximum number of events to retrieve
            
        Returns:
            List of event descriptions, most recent first
        """
        key = self._key(user_id)
        vals = await self.redis.lrange(key, 0, limit - 1)
        return [v.decode() if isinstance(v, bytes) else v for v in vals]


async def build_memory_store(settings) -> Optional[BaseMemoryStore]:
    """Build and initialize appropriate memory store.
    
    Attempts to use Redis if configured, falls back to in-memory storage.
    
    Args:
        settings: Application settings object
        
    Returns:
        Initialized memory store instance, or None if disabled
    """
    if not getattr(settings, 'MEMORY_ENABLED', True):
        logger.info("Memory disabled via settings")
        return None

    max_events = getattr(settings, 'MEMORY_MAX_EVENTS', 50)
    ttl_days = getattr(settings, 'MEMORY_TTL_DAYS', 7)

    if getattr(settings, 'REDIS_URL', None) and Redis is not None:
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
            if await redis.ping():
                logger.info("Using Redis memory store: %s", settings.REDIS_URL)
                return RedisMemoryStore(redis, max_events, ttl_days)
        except Exception as e:
            logger.warning(
                "Redis memory init failed, fallback to in-memory: %s",
                str(e)
            )

    logger.info("Using in-memory memory store")
    return InMemoryMemoryStore(max_events, ttl_days)
