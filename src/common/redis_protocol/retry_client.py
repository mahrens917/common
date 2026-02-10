"""Redis client wrapper with automatic operation-level retry."""

from __future__ import annotations

from typing import Any, List, Optional

from .retry import RedisRetryPolicy, with_redis_retry
from .retry_client_mixins import RetryRedisCollectionMixin, RetryRedisHashMixin, RetryRedisSortedSetMixin
from .retry_client_stream_mixin import RetryRedisStreamMixin
from .retry_pipeline_mixins import RetryPipelineHashMixin, RetryPipelineSortedSetMixin
from .typing import ensure_awaitable


class RetryPipeline(RetryPipelineHashMixin, RetryPipelineSortedSetMixin):
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

    def setnx(self, name: str, value: Any) -> "RetryPipeline":
        self._pipeline.setnx(name, value)
        return self

    def get(self, name: str) -> "RetryPipeline":
        self._pipeline.get(name)
        return self

    def lpush(self, name: str, *values: Any) -> "RetryPipeline":
        self._pipeline.lpush(name, *values)
        return self

    def ltrim(self, name: str, start: int, end: int) -> "RetryPipeline":
        self._pipeline.ltrim(name, start, end)
        return self

    def delete(self, *names: str) -> "RetryPipeline":
        self._pipeline.delete(*names)
        return self

    def expire(self, name: str, time: int) -> "RetryPipeline":
        self._pipeline.expire(name, time)
        return self

    async def execute(self, *, raise_on_error: bool = True, context: str = "pipeline.execute") -> List[Any]:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._pipeline.execute(raise_on_error=raise_on_error)),
            context=context,
            policy=self._policy,
        )


class RetryRedisClient(RetryRedisHashMixin, RetryRedisSortedSetMixin, RetryRedisCollectionMixin, RetryRedisStreamMixin):
    """Redis client wrapper with automatic operation-level retry."""

    def __init__(self, redis_client: Any, *, policy: Optional[RedisRetryPolicy] = None) -> None:
        self._client = redis_client
        self._policy = policy

    def pipeline(self, **kwargs: Any) -> RetryPipeline:
        return RetryPipeline(self._client.pipeline(**kwargs), policy=self._policy)

    def close(self) -> None:
        self._client.close()

    async def aclose(self) -> None:
        await self._client.aclose()

    def pubsub(self, **kwargs: Any) -> Any:
        return self._client.pubsub(**kwargs)


__all__ = ["RetryPipeline", "RetryRedisClient"]
