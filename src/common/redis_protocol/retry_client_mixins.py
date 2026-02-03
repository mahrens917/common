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

    async def hscan(
        self,
        name: str,
        cursor: int = 0,
        match: Optional[str] = None,
        count: Optional[int] = None,
        *,
        context: str = "hscan",
    ) -> Any:
        kwargs: dict[str, Any] = {}
        if match is not None:
            kwargs["match"] = match
        if count is not None:
            kwargs["count"] = count
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.hscan(name, cursor, **kwargs)),
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
        kwargs: dict[str, Any] = {}
        if ex is not None:
            kwargs["ex"] = ex
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.set(name, value, **kwargs)),
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

    async def exists(self, *names: str, context: str = "exists") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.exists(*names)),
            context=context,
            policy=self._policy,
        )

    async def ping(self, *, context: str = "ping") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.ping()),
            context=context,
            policy=self._policy,
        )


class RetryRedisSortedSetMixin:
    """Sorted set operations with retry."""

    _client: Any
    _policy: Optional[RedisRetryPolicy]

    async def zadd(self, name: str, mapping: Any, *, context: str = "zadd") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.zadd(name, mapping)),
            context=context,
            policy=self._policy,
        )

    async def zrange(self, name: str, start: int, end: int, *, withscores: bool = False, context: str = "zrange") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.zrange(name, start, end, withscores=withscores)),
            context=context,
            policy=self._policy,
        )

    async def zrangebyscore(
        self,
        name: str,
        min_score: Any,
        max_score: Any,
        *,
        withscores: bool = False,
        context: str = "zrangebyscore",
    ) -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.zrangebyscore(name, min_score, max_score, withscores=withscores)),
            context=context,
            policy=self._policy,
        )

    async def zremrangebyscore(self, name: str, min_score: Any, max_score: Any, *, context: str = "zremrangebyscore") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.zremrangebyscore(name, min_score, max_score)),
            context=context,
            policy=self._policy,
        )

    async def zcount(self, name: str, min_score: Any, max_score: Any, *, context: str = "zcount") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.zcount(name, min_score, max_score)),
            context=context,
            policy=self._policy,
        )


class RetryRedisCollectionMixin:
    """List, pub/sub and scan operations with retry."""

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

    async def config_get(self, pattern: str, *, context: str = "config_get") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.config_get(pattern)),
            context=context,
            policy=self._policy,
        )

    async def config_set(self, name: str, value: Any, *, context: str = "config_set") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.config_set(name, value)),
            context=context,
            policy=self._policy,
        )


__all__ = ["RetryRedisCollectionMixin", "RetryRedisHashMixin", "RetryRedisSortedSetMixin"]
