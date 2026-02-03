"""Mixin classes for RetryRedisClient operations."""

from __future__ import annotations

from typing import Any, Optional

from .retry import RedisRetryPolicy, with_redis_retry
from .typing import ensure_awaitable


class RetryRedisHashMixin:
    """Hash and key-value operations with retry."""

    _client: Any
    _policy: Optional[RedisRetryPolicy]

    async def hset(self, name: str, mapping: Any = None, *, context: str = "hset", **kwargs: Any) -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.hset(name, mapping=mapping, **kwargs)),
            context=context,
            policy=self._policy,
        )

    async def hget(self, name: str, key: str, *, context: str = "hget") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.hget(name, key)),
            context=context,
            policy=self._policy,
        )

    async def hmget(self, name: str, *keys: str, context: str = "hmget") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.hmget(name, *keys)),
            context=context,
            policy=self._policy,
        )

    async def hgetall(self, name: str, *, context: str = "hgetall") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.hgetall(name)),
            context=context,
            policy=self._policy,
        )

    async def hdel(self, name: str, *keys: str, context: str = "hdel") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.hdel(name, *keys)),
            context=context,
            policy=self._policy,
        )

    async def get(self, name: str, *, context: str = "get") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.get(name)),
            context=context,
            policy=self._policy,
        )

    async def set(self, name: str, value: Any, *, ex: Optional[int] = None, context: str = "set") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.set(name, value, ex=ex)),
            context=context,
            policy=self._policy,
        )

    async def expire(self, name: str, time: int, *, context: str = "expire") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.expire(name, time)),
            context=context,
            policy=self._policy,
        )

    async def type(self, name: str, *, context: str = "type") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.type(name)),
            context=context,
            policy=self._policy,
        )


class RetryRedisCollectionMixin:
    """List, set, pub/sub and scan operations with retry."""

    _client: Any
    _policy: Optional[RedisRetryPolicy]

    async def publish(self, channel: str, message: Any, *, context: str = "publish") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.publish(channel, message)),
            context=context,
            policy=self._policy,
        )

    async def delete(self, *names: str, context: str = "delete") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.delete(*names)),
            context=context,
            policy=self._policy,
        )

    async def lrange(self, name: str, start: int, end: int, *, context: str = "lrange") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.lrange(name, start, end)),
            context=context,
            policy=self._policy,
        )

    async def lpush(self, name: str, *values: Any, context: str = "lpush") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.lpush(name, *values)),
            context=context,
            policy=self._policy,
        )

    async def zadd(self, name: str, mapping: Any, *, context: str = "zadd") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.zadd(name, mapping)),
            context=context,
            policy=self._policy,
        )

    async def scan(
        self,
        cursor: int = 0,
        match: Optional[str] = None,
        count: Optional[int] = None,
        *,
        context: str = "scan",
    ) -> Any:
        kwargs: dict[str, Any] = {}
        if match is not None:
            kwargs["match"] = match
        if count is not None:
            kwargs["count"] = count
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.scan(cursor, **kwargs)),
            context=context,
            policy=self._policy,
        )

    async def keys(self, pattern: str = "*", *, context: str = "keys") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.keys(pattern)),
            context=context,
            policy=self._policy,
        )

    async def info(self, *, context: str = "info") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.info()),
            context=context,
            policy=self._policy,
        )


__all__ = ["RetryRedisHashMixin", "RetryRedisCollectionMixin"]
