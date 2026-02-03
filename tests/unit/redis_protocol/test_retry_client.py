"""Tests for RetryRedisClient and RetryPipeline."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from common.redis_protocol.retry import RedisRetryError, RedisRetryPolicy
from common.redis_protocol.retry_client import RetryPipeline, RetryRedisClient

_INITIAL_FAILURE = 1
_SUCCESSFUL_RETRY = 1
EXPECTED_RETRY_ATTEMPTS = _INITIAL_FAILURE + _SUCCESSFUL_RETRY


def _fast_policy() -> RedisRetryPolicy:
    return RedisRetryPolicy(
        max_attempts=3,
        initial_delay=0.01,
        max_delay=0.01,
        multiplier=1.0,
        jitter_ratio=0.0,
    )


def _make_mock_redis() -> MagicMock:
    mock = MagicMock()
    for method_name in (
        "hset",
        "hget",
        "hmget",
        "hgetall",
        "hdel",
        "get",
        "set",
        "expire",
        "type",
        "publish",
        "delete",
        "lrange",
        "lpush",
        "zadd",
        "scan",
        "keys",
        "info",
    ):
        setattr(mock, method_name, AsyncMock())
    mock.aclose = AsyncMock()
    mock.pubsub = MagicMock()
    pipe_mock = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[])
    pipe_mock.hset = MagicMock(return_value=pipe_mock)
    pipe_mock.hgetall = MagicMock(return_value=pipe_mock)
    pipe_mock.lpush = MagicMock(return_value=pipe_mock)
    pipe_mock.hmget = MagicMock(return_value=pipe_mock)
    mock.pipeline = MagicMock(return_value=pipe_mock)
    return mock


@pytest.mark.asyncio
async def test_hset_retries_on_transient_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    mock_redis = _make_mock_redis()
    attempts: list[int] = []

    async def flaky_hset(*args, **kwargs):
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise RedisConnectionError("connection lost")
        return 1

    mock_redis.hset = flaky_hset
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    result = await client.hset("key", mapping={"field": "value"})
    assert result == 1
    assert len(attempts) == EXPECTED_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_get_succeeds_first_try():
    mock_redis = _make_mock_redis()
    mock_redis.get = AsyncMock(return_value=b"hello")
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.get("mykey") == b"hello"


@pytest.mark.asyncio
async def test_exhausted_retries_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    mock_redis = _make_mock_redis()
    mock_redis.hget = AsyncMock(side_effect=RedisConnectionError("down"))
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    with pytest.raises(RedisRetryError):
        await client.hget("key", "field")


@pytest.mark.asyncio
async def test_pipeline_execute_retries(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    raw_pipe = MagicMock()
    attempts: list[int] = []

    async def flaky_execute(raise_on_error: bool = True):
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise RedisConnectionError("pipe error")
        return [1, 2]

    raw_pipe.execute = flaky_execute
    raw_pipe.hset = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe, policy=_fast_policy())
    pipe.hset("key", mapping={"f": "v"})
    result = await pipe.execute()
    assert result == [1, 2]
    assert len(attempts) == EXPECTED_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_set_with_expiry():
    mock_redis = _make_mock_redis()
    mock_redis.set = AsyncMock(return_value=True)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.set("k", "v", ex=60) is True


@pytest.mark.asyncio
async def test_scan_passes_kwargs():
    mock_redis = _make_mock_redis()
    mock_redis.scan = AsyncMock(return_value=(0, [b"key1"]))
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.scan(cursor=0, match="prefix:*", count=100) == (0, [b"key1"])


@pytest.mark.asyncio
async def test_delete_multiple_keys():
    mock_redis = _make_mock_redis()
    mock_redis.delete = AsyncMock(return_value=EXPECTED_RETRY_ATTEMPTS)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.delete("k1", "k2") == EXPECTED_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_aclose_delegates():
    mock_redis = _make_mock_redis()
    client = RetryRedisClient(mock_redis)
    await client.aclose()
    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_pubsub_delegates():
    mock_redis = _make_mock_redis()
    sentinel = object()
    mock_redis.pubsub.return_value = sentinel
    client = RetryRedisClient(mock_redis)
    assert client.pubsub() is sentinel


@pytest.mark.asyncio
async def test_pipeline_chaining():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[1, 2, 3])
    raw_pipe.hset = MagicMock(return_value=raw_pipe)
    raw_pipe.lpush = MagicMock(return_value=raw_pipe)
    raw_pipe.hmget = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe)
    result_pipe = pipe.hset("key", mapping={"a": "b"}).lpush("list", "val")
    assert isinstance(result_pipe, RetryPipeline)
    assert await pipe.execute() == [1, 2, 3]


@pytest.mark.asyncio
async def test_hmget_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.hmget = AsyncMock(return_value=[b"v1", b"v2"])
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.hmget("hash", "f1", "f2") == [b"v1", b"v2"]


@pytest.mark.asyncio
async def test_hgetall_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.hgetall = AsyncMock(return_value={b"f": b"v"})
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.hgetall("hash") == {b"f": b"v"}


@pytest.mark.asyncio
async def test_hdel_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.hdel = AsyncMock(return_value=1)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.hdel("hash", "field") == 1


@pytest.mark.asyncio
async def test_expire_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.expire = AsyncMock(return_value=True)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.expire("key", 60) is True


@pytest.mark.asyncio
async def test_type_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.type = AsyncMock(return_value=b"hash")
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.type("key") == b"hash"


@pytest.mark.asyncio
async def test_publish_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.publish = AsyncMock(return_value=1)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.publish("channel", "msg") == 1


@pytest.mark.asyncio
async def test_lrange_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.lrange = AsyncMock(return_value=[b"a", b"b"])
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.lrange("list", 0, -1) == [b"a", b"b"]


@pytest.mark.asyncio
async def test_lpush_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.lpush = AsyncMock(return_value=1)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.lpush("list", "val") == 1


@pytest.mark.asyncio
async def test_zadd_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.zadd = AsyncMock(return_value=1)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.zadd("set", {"member": 1.0}) == 1


@pytest.mark.asyncio
async def test_keys_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.keys = AsyncMock(return_value=[b"k1"])
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.keys("k*") == [b"k1"]


@pytest.mark.asyncio
async def test_info_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.info = AsyncMock(return_value={"redis_version": "7.0"})
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.info() == {"redis_version": "7.0"}


@pytest.mark.asyncio
async def test_pipeline_hgetall():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[{b"f": b"v"}])
    raw_pipe.hgetall = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe)
    result = pipe.hgetall("key")
    assert isinstance(result, RetryPipeline)
    assert await pipe.execute() == [{b"f": b"v"}]


@pytest.mark.asyncio
async def test_pipeline_hmget():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[[b"v1"]])
    raw_pipe.hmget = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe)
    result = pipe.hmget("key", "f1")
    assert isinstance(result, RetryPipeline)
    assert await pipe.execute() == [[b"v1"]]


@pytest.mark.asyncio
async def test_scan_without_optional_kwargs():
    mock_redis = _make_mock_redis()
    mock_redis.scan = AsyncMock(return_value=(0, []))
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.scan() == (0, [])


@pytest.mark.asyncio
async def test_pipeline_lpush():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[1])
    raw_pipe.lpush = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe)
    result = pipe.lpush("list", "v1", "v2")
    assert isinstance(result, RetryPipeline)
    assert await pipe.execute() == [1]


@pytest.mark.asyncio
async def test_hscan_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.hscan = AsyncMock(return_value=(0, {b"f": b"v"}))
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.hscan("hash", match="f*") == (0, {b"f": b"v"})


@pytest.mark.asyncio
async def test_exists_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.exists = AsyncMock(return_value=1)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.exists("key") == 1


@pytest.mark.asyncio
async def test_ping_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.ping = AsyncMock(return_value=True)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.ping() is True


@pytest.mark.asyncio
async def test_zrange_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.zrange = AsyncMock(return_value=[b"m1"])
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.zrange("set", 0, -1) == [b"m1"]


@pytest.mark.asyncio
async def test_zrangebyscore_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.zrangebyscore = AsyncMock(return_value=[b"m1"])
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.zrangebyscore("set", "-inf", "+inf") == [b"m1"]


@pytest.mark.asyncio
async def test_zremrangebyscore_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.zremrangebyscore = AsyncMock(return_value=1)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.zremrangebyscore("set", 0, 100) == 1


@pytest.mark.asyncio
async def test_zcount_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.zcount = AsyncMock(return_value=5)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.zcount("set", "-inf", "+inf") == 5


@pytest.mark.asyncio
async def test_config_get_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.config_get = AsyncMock(return_value={"maxmemory": "0"})
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.config_get("maxmemory") == {"maxmemory": "0"}


@pytest.mark.asyncio
async def test_config_set_delegates():
    mock_redis = _make_mock_redis()
    mock_redis.config_set = AsyncMock(return_value=True)
    client = RetryRedisClient(mock_redis, policy=_fast_policy())
    assert await client.config_set("maxmemory", "100mb") is True


@pytest.mark.asyncio
async def test_pipeline_sorted_set_operations():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[1, 0, 1])
    for m in ("zadd", "zremrangebyscore", "expire"):
        setattr(raw_pipe, m, MagicMock(return_value=raw_pipe))
    pipe = RetryPipeline(raw_pipe)
    pipe.zadd("set", {"m": 1.0}).zremrangebyscore("set", 0, 0).expire("set", 86400)
    assert await pipe.execute() == [1, 0, 1]


@pytest.mark.asyncio
async def test_pipeline_delete_and_hset():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[1, 1])
    raw_pipe.delete = MagicMock(return_value=raw_pipe)
    raw_pipe.hset = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe)
    pipe.delete("key").hset("key", mapping={"f": "v"})
    assert await pipe.execute() == [1, 1]


@pytest.mark.asyncio
async def test_pipeline_zrange_and_zcount():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[[b"m1"], 5])
    raw_pipe.zrange = MagicMock(return_value=raw_pipe)
    raw_pipe.zcount = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe)
    pipe.zrange("set", -1, -1, withscores=True).zcount("set", 0, "+inf")
    assert await pipe.execute() == [[b"m1"], 5]


@pytest.mark.asyncio
async def test_pipeline_hget_hdel_ltrim():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[b"v", 1, True])
    raw_pipe.hget = MagicMock(return_value=raw_pipe)
    raw_pipe.hdel = MagicMock(return_value=raw_pipe)
    raw_pipe.ltrim = MagicMock(return_value=raw_pipe)
    pipe = RetryPipeline(raw_pipe)
    pipe.hget("h", "f").hdel("h", "f2").ltrim("list", 0, 99)
    assert await pipe.execute() == [b"v", 1, True]


@pytest.mark.asyncio
async def test_pipeline_execute_raise_on_error_false():
    raw_pipe = MagicMock()
    raw_pipe.execute = AsyncMock(return_value=[1])
    pipe = RetryPipeline(raw_pipe)
    await pipe.execute(raise_on_error=False)
    raw_pipe.execute.assert_awaited_once()
