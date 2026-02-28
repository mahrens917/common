"""Tests for RetryRedisStreamMixin."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import ResponseError

from common.redis_protocol.retry import RedisFatalError, RedisRetryPolicy
from common.redis_protocol.retry_client_stream_mixin import RetryRedisStreamMixin


def _fast_policy() -> RedisRetryPolicy:
    return RedisRetryPolicy(
        max_attempts=3,
        initial_delay=0.01,
        max_delay=0.01,
        multiplier=1.0,
        jitter_ratio=0.0,
    )


def _make_mixin() -> RetryRedisStreamMixin:
    mock_client = MagicMock()
    for method_name in ("xadd", "xreadgroup", "xack", "xautoclaim", "xgroup_create", "xlen"):
        setattr(mock_client, method_name, AsyncMock())
    mixin = RetryRedisStreamMixin.__new__(RetryRedisStreamMixin)
    mixin._client = mock_client
    mixin._policy = _fast_policy()
    return mixin


class TestXadd:
    @pytest.mark.asyncio
    async def test_xadd_delegates(self):
        mixin = _make_mixin()
        mixin._client.xadd = AsyncMock(return_value=b"123-0")
        result = await mixin.xadd("stream", {"key": "val"})
        assert result == b"123-0"
        mixin._client.xadd.assert_awaited_once_with("stream", {"key": "val"})

    @pytest.mark.asyncio
    async def test_xadd_with_maxlen(self):
        mixin = _make_mixin()
        mixin._client.xadd = AsyncMock(return_value=b"123-0")
        await mixin.xadd("stream", {"k": "v"}, maxlen=1000, approximate=False)
        mixin._client.xadd.assert_awaited_once_with(
            "stream",
            {"k": "v"},
            maxlen=1000,
            approximate=False,
        )


class TestXreadgroup:
    @pytest.mark.asyncio
    async def test_xreadgroup_delegates(self):
        mixin = _make_mixin()
        mixin._client.xreadgroup = AsyncMock(return_value=[])
        result = await mixin.xreadgroup("grp", "consumer1", {"stream": ">"})
        assert result == []
        mixin._client.xreadgroup.assert_awaited_once_with("grp", "consumer1", {"stream": ">"})

    @pytest.mark.asyncio
    async def test_xreadgroup_with_count_and_block(self):
        mixin = _make_mixin()
        mixin._client.xreadgroup = AsyncMock(return_value=[])
        await mixin.xreadgroup("grp", "c1", {"s": ">"}, count=10, block=5000)
        mixin._client.xreadgroup.assert_awaited_once_with(
            "grp",
            "c1",
            {"s": ">"},
            count=10,
            block=5000,
        )


class TestXack:
    @pytest.mark.asyncio
    async def test_xack_delegates(self):
        mixin = _make_mixin()
        mixin._client.xack = AsyncMock(return_value=1)
        result = await mixin.xack("stream", "grp", "123-0")
        assert result == 1
        mixin._client.xack.assert_awaited_once_with("stream", "grp", "123-0")


class TestXautoclaim:
    @pytest.mark.asyncio
    async def test_xautoclaim_delegates(self):
        mixin = _make_mixin()
        mixin._client.xautoclaim = AsyncMock(return_value=(b"0-0", []))
        result = await mixin.xautoclaim("stream", "grp", "consumer1", 60000)
        assert result == (b"0-0", [])
        mixin._client.xautoclaim.assert_awaited_once_with(
            "stream",
            "grp",
            "consumer1",
            60000,
            start_id="0-0",
        )

    @pytest.mark.asyncio
    async def test_xautoclaim_with_count(self):
        mixin = _make_mixin()
        mixin._client.xautoclaim = AsyncMock(return_value=(b"0-0", []))
        await mixin.xautoclaim("stream", "grp", "c1", 60000, count=5, start_id="100-0")
        mixin._client.xautoclaim.assert_awaited_once_with(
            "stream",
            "grp",
            "c1",
            60000,
            start_id="100-0",
            count=5,
        )


class TestXgroupCreate:
    @pytest.mark.asyncio
    async def test_xgroup_create_delegates(self):
        mixin = _make_mixin()
        mixin._client.xgroup_create = AsyncMock(return_value=True)
        result = await mixin.xgroup_create("stream", "grp")
        assert result is True
        mixin._client.xgroup_create.assert_awaited_once_with(
            "stream",
            "grp",
            id="0",
            mkstream=False,
        )

    @pytest.mark.asyncio
    async def test_xgroup_create_with_mkstream(self):
        mixin = _make_mixin()
        mixin._client.xgroup_create = AsyncMock(return_value=True)
        await mixin.xgroup_create("stream", "grp", id="$", mkstream=True)
        mixin._client.xgroup_create.assert_awaited_once_with(
            "stream",
            "grp",
            id="$",
            mkstream=True,
        )

    @pytest.mark.asyncio
    async def test_xgroup_create_busygroup_aborts_retry(self):
        """BUSYGROUP raises RedisFatalError immediately — no retries."""
        mixin = _make_mixin()
        mixin._client.xgroup_create = AsyncMock(
            side_effect=ResponseError("BUSYGROUP Consumer Group name already exists"),
        )
        with pytest.raises(RedisFatalError, match="already exists"):
            await mixin.xgroup_create("stream", "grp")
        # Called only once — no retries for BUSYGROUP
        assert mixin._client.xgroup_create.await_count == 1


class TestXlen:
    @pytest.mark.asyncio
    async def test_xlen_delegates(self):
        mixin = _make_mixin()
        mixin._client.xlen = AsyncMock(return_value=42)
        result = await mixin.xlen("stream")
        assert result == 42
        mixin._client.xlen.assert_awaited_once_with("stream")
