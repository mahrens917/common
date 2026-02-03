"""Redis client wrapper with automatic operation-level retry."""

from __future__ import annotations

from typing import Any, List, Optional

from .retry import RedisRetryPolicy, with_redis_retry
from .retry_client_mixins import RetryRedisCollectionMixin, RetryRedisHashMixin
from .typing import ensure_awaitable


class RetryPipeline:
    """Pipeline wrapper that retries execute() on transient errors."""

    def __init__(self, pipeline: Any, *, policy: Optional[RedisRetryPolicy] = None) -> None:
        self._pipeline = pipeline
        self._policy = policy

    def hset(self, name: str, mapping: Any = None, **kwargs: Any) -> "RetryPipeline":
        self._pipeline.hset(name, mapping=mapping, **kwargs)
        return self

    def hgetall(self, name: str) -> "RetryPipeline":
        self._pipeline.hgetall(name)
        return self

    def lpush(self, name: str, *values: Any) -> "RetryPipeline":
        self._pipeline.lpush(name, *values)
        return self

    def hmget(self, name: str, *keys: str) -> "RetryPipeline":
        self._pipeline.hmget(name, *keys)
        return self

    async def execute(self, *, context: str = "pipeline.execute") -> List[Any]:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._pipeline.execute()),
            context=context,
            policy=self._policy,
        )


class RetryRedisClient(RetryRedisHashMixin, RetryRedisCollectionMixin):
    """Redis client wrapper with automatic operation-level retry."""

    def __init__(self, redis_client: Any, *, policy: Optional[RedisRetryPolicy] = None) -> None:
        self._client = redis_client
        self._policy = policy

    def pipeline(self) -> RetryPipeline:
        return RetryPipeline(self._client.pipeline(), policy=self._policy)

    async def aclose(self) -> None:
        await self._client.aclose()

    def pubsub(self) -> Any:
        return self._client.pubsub()


__all__ = ["RetryPipeline", "RetryRedisClient"]
