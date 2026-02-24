"""Mixin classes for RetryPipeline operations."""

from __future__ import annotations

from typing import Any, Self


class RetryPipelineHashMixin:
    """Hash operations for pipeline."""

    _pipeline: Any

    def hset(self, name: str, *args: Any, **kwargs: Any) -> Self:
        self._pipeline.hset(name, *args, **kwargs)
        return self

    def hgetall(self, name: str) -> Self:
        self._pipeline.hgetall(name)
        return self

    def hget(self, name: str, key: str) -> Self:
        self._pipeline.hget(name, key)
        return self

    def hdel(self, name: str, *keys: str) -> Self:
        self._pipeline.hdel(name, *keys)
        return self

    def hincrby(self, name: str, key: str, amount: int = 1) -> Self:
        self._pipeline.hincrby(name, key, amount)
        return self

    def hmget(self, name: str, *keys: str) -> Self:
        self._pipeline.hmget(name, *keys)
        return self


class RetryPipelineSortedSetMixin:
    """Sorted set operations for pipeline."""

    _pipeline: Any

    def zadd(self, name: str, mapping: Any) -> Self:
        self._pipeline.zadd(name, mapping)
        return self

    def zremrangebyscore(self, name: str, min_score: Any, max_score: Any) -> Self:
        self._pipeline.zremrangebyscore(name, min_score, max_score)
        return self

    def zrange(self, name: str, start: int, end: int, *, withscores: bool = False) -> Self:
        self._pipeline.zrange(name, start, end, withscores=withscores)
        return self

    def zrangebyscore(self, name: str, min_score: Any, max_score: Any, *, withscores: bool = False) -> Self:
        self._pipeline.zrangebyscore(name, min_score, max_score, withscores=withscores)
        return self

    def zcount(self, name: str, min_score: Any, max_score: Any) -> Self:
        self._pipeline.zcount(name, min_score, max_score)
        return self


class RetryPipelineSetMixin:
    """Set operations for pipeline."""

    _pipeline: Any

    def sadd(self, name: str, *values: Any) -> Self:
        self._pipeline.sadd(name, *values)
        return self

    def srem(self, name: str, *values: Any) -> Self:
        self._pipeline.srem(name, *values)
        return self


__all__ = ["RetryPipelineHashMixin", "RetryPipelineSetMixin", "RetryPipelineSortedSetMixin"]
