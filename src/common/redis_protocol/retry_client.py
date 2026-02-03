"""Redis client wrapper with automatic operation-level retry."""

from __future__ import annotations

from typing import Any, List, Optional

from .retry import RedisRetryPolicy, with_redis_retry
from .retry_client_mixins import RetryRedisCollectionMixin, RetryRedisHashMixin, RetryRedisSortedSetMixin
from .typing import ensure_awaitable


class RetryPipeline:
    """Pipeline wrapper that retries execute() on transient errors."""

    def __init__(self, pipeline: Any, *, policy: Optional[RedisRetryPolicy] = None) -> None:
        self._pipeline = pipeline
        self._policy = policy

    async def __aenter__(self) -> "RetryPipeline":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._pipeline.__aexit__(exc_type, exc_val, exc_tb)

    def set(self, name: str, value: Any, **kwargs: Any) -> "RetryPipeline":
        self._pipeline.set(name, value, **kwargs)
        return self

    def get(self, name: str) -> "RetryPipeline":
        self._pipeline.get(name)
        return self

    def hset(self, name: str, *args: Any, **kwargs: Any) -> "RetryPipeline":
        self._pipeline.hset(name, *args, **kwargs)
        return self

    def hgetall(self, name: str) -> "RetryPipeline":
        self._pipeline.hgetall(name)
        return self

    def hget(self, name: str, key: str) -> "RetryPipeline":
        self._pipeline.hget(name, key)
        return self

    def hdel(self, name: str, *keys: str) -> "RetryPipeline":
        self._pipeline.hdel(name, *keys)
        return self

    def hincrby(self, name: str, key: str, amount: int = 1) -> "RetryPipeline":
        self._pipeline.hincrby(name, key, amount)
        return self

    def lpush(self, name: str, *values: Any) -> "RetryPipeline":
        self._pipeline.lpush(name, *values)
        return self

    def ltrim(self, name: str, start: int, end: int) -> "RetryPipeline":
        self._pipeline.ltrim(name, start, end)
        return self

    def hmget(self, name: str, *keys: str) -> "RetryPipeline":
        self._pipeline.hmget(name, *keys)
        return self

    def delete(self, *names: str) -> "RetryPipeline":
        self._pipeline.delete(*names)
        return self

    def expire(self, name: str, time: int) -> "RetryPipeline":
        self._pipeline.expire(name, time)
        return self

    def zadd(self, name: str, mapping: Any) -> "RetryPipeline":
        self._pipeline.zadd(name, mapping)
        return self

    def zremrangebyscore(self, name: str, min_score: Any, max_score: Any) -> "RetryPipeline":
        self._pipeline.zremrangebyscore(name, min_score, max_score)
        return self

    def zrange(self, name: str, start: int, end: int, *, withscores: bool = False) -> "RetryPipeline":
        self._pipeline.zrange(name, start, end, withscores=withscores)
        return self

    def zrangebyscore(self, name: str, min_score: Any, max_score: Any, *, withscores: bool = False) -> "RetryPipeline":
        self._pipeline.zrangebyscore(name, min_score, max_score, withscores=withscores)
        return self

    def zcount(self, name: str, min_score: Any, max_score: Any) -> "RetryPipeline":
        self._pipeline.zcount(name, min_score, max_score)
        return self

    async def execute(self, *, raise_on_error: bool = True, context: str = "pipeline.execute") -> List[Any]:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._pipeline.execute(raise_on_error=raise_on_error)),
            context=context,
            policy=self._policy,
        )


class RetryRedisClient(RetryRedisHashMixin, RetryRedisSortedSetMixin, RetryRedisCollectionMixin):
    """Redis client wrapper with automatic operation-level retry."""

    def __init__(self, redis_client: Any, *, policy: Optional[RedisRetryPolicy] = None) -> None:
        self._client = redis_client
        self._policy = policy

    def pipeline(self, **kwargs: Any) -> RetryPipeline:
        return RetryPipeline(self._client.pipeline(**kwargs), policy=self._policy)

    async def aclose(self) -> None:
        await self._client.aclose()

    def pubsub(self, **kwargs: Any) -> Any:
        return self._client.pubsub(**kwargs)


__all__ = ["RetryPipeline", "RetryRedisClient"]
