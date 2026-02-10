"""Mixin adding Redis Streams operations with retry to RetryRedisClient."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from .retry import RedisRetryPolicy, with_redis_retry
from .typing import ensure_awaitable


class RetryRedisStreamMixin:
    """Stream operations with retry."""

    _client: Any
    _policy: Optional[RedisRetryPolicy]

    async def xadd(
        self,
        name: str,
        fields: dict,
        *,
        maxlen: Optional[int] = None,
        approximate: bool = True,
        context: str = "xadd",
    ) -> Any:
        kwargs: dict[str, Any] = {}
        if maxlen is not None:
            kwargs["maxlen"] = maxlen
            kwargs["approximate"] = approximate
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.xadd(name, fields, **kwargs)),
            context=context,
            policy=self._policy,
        )

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        *,
        count: Optional[int] = None,
        block: Optional[int] = None,
        context: str = "xreadgroup",
    ) -> Any:
        kwargs: dict[str, Any] = {}
        if count is not None:
            kwargs["count"] = count
        if block is not None:
            kwargs["block"] = block
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.xreadgroup(groupname, consumername, streams, **kwargs)),
            context=context,
            policy=self._policy,
        )

    async def xack(self, name: str, groupname: str, *ids: str, context: str = "xack") -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.xack(name, groupname, *ids)),
            context=context,
            policy=self._policy,
        )

    async def xautoclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        *,
        start_id: str = "0-0",
        count: Optional[int] = None,
        context: str = "xautoclaim",
    ) -> Any:
        kwargs: dict[str, Any] = {"start_id": start_id}
        if count is not None:
            kwargs["count"] = count
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.xautoclaim(name, groupname, consumername, min_idle_time, **kwargs)),
            context=context,
            policy=self._policy,
        )

    async def xgroup_create(
        self,
        name: str,
        groupname: str,
        *,
        id: str = "0",
        mkstream: bool = False,
        context: str = "xgroup_create",
    ) -> Any:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.xgroup_create(name, groupname, id=id, mkstream=mkstream)),
            context=context,
            policy=self._policy,
        )

    async def xlen(self, name: str, *, context: str = "xlen") -> int:
        return await with_redis_retry(
            lambda: ensure_awaitable(self._client.xlen(name)),
            context=context,
            policy=self._policy,
        )


__all__: List[str] = ["RetryRedisStreamMixin"]
