from unittest.mock import AsyncMock

import pytest

from src.common.redis_protocol.atomic_operations import (
    AtomicRedisOperations,
    RedisDataValidationError,
)

_CONST_11 = 11
_TEST_COUNT_10 = 10
_TEST_COUNT_2 = 2


class _FakePipeline:
    def __init__(self):
        self.mapping = None
        self.executed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def hset(self, key, *, mapping):
        self.mapping = mapping
        return self

    async def execute(self):
        self.executed = True
        return [True]


class _RedisStub:
    def __init__(self, *, pipeline_obj=None, hgetall=None, delete=None):
        self._pipeline_obj = pipeline_obj
        self.hgetall = hgetall or AsyncMock(return_value={})
        self.delete = delete or AsyncMock(return_value=0)

    def pipeline(self, *args, **kwargs):
        if self._pipeline_obj is None:
            raise AssertionError("pipeline called unexpectedly")
        return self._pipeline_obj


@pytest.mark.asyncio
async def test_atomic_market_data_write_enforces_string_mapping():
    fake_pipe = _FakePipeline()
    redis = _RedisStub(pipeline_obj=fake_pipe)

    ops = AtomicRedisOperations(redis)
    payload = {"best_bid": 10.5, "best_ask": 11}

    ok = await ops.atomic_market_data_write("market:1", payload)

    assert ok is True
    assert fake_pipe.executed is True
    assert fake_pipe.mapping["best_bid"] == "10.5"
    assert fake_pipe.mapping["best_ask"] == "11"
    assert "last_update" in fake_pipe.mapping


@pytest.mark.asyncio
async def test_safe_market_data_read_validates_required_fields():
    redis = _RedisStub(
        hgetall=AsyncMock(
            side_effect=[
                {"best_bid": "10"},
                {
                    "best_bid": "10",
                    "best_ask": "11",
                    "best_bid_size": "1",
                    "best_ask_size": "1",
                },
            ]
        )
    )

    ops = AtomicRedisOperations(redis)
    result = await ops.safe_market_data_read("market:1", required_fields=["best_bid", "best_ask"])

    assert result["best_bid"] == _TEST_COUNT_10
    assert result["best_ask"] == _CONST_11
    assert redis.hgetall.await_count == _TEST_COUNT_2


@pytest.mark.asyncio
async def test_safe_market_data_read_invalid_spread_retries():
    redis = _RedisStub(
        hgetall=AsyncMock(
            side_effect=[
                {
                    "best_bid": "12",
                    "best_ask": "11",
                    "best_bid_size": "1",
                    "best_ask_size": "1",
                },
                {
                    "best_bid": "10",
                    "best_ask": "11",
                    "best_bid_size": "1",
                    "best_ask_size": "1",
                },
            ]
        )
    )

    ops = AtomicRedisOperations(redis)
    result = await ops.safe_market_data_read("market:1")

    assert result["best_bid"] == _TEST_COUNT_10
    assert result["best_ask"] == _CONST_11
    assert redis.hgetall.await_count == _TEST_COUNT_2


@pytest.mark.asyncio
async def test_atomic_delete_if_invalid_removes_key():
    delete_mock = AsyncMock(return_value=1)
    redis = _RedisStub(delete=delete_mock)
    ops = AtomicRedisOperations(redis)

    deleted = await ops.atomic_delete_if_invalid(
        "market:1",
        {"best_bid": 0, "best_ask": 11, "best_bid_size": 1, "best_ask_size": 1},
    )

    assert deleted is True
    delete_mock.assert_awaited_once_with("market:1")


@pytest.mark.asyncio
async def test_atomic_market_data_write_handles_empty_results():
    class _EmptyPipeline(_FakePipeline):
        async def execute(self):
            self.executed = True
            return []

    fake_pipe = _EmptyPipeline()
    redis = _RedisStub(pipeline_obj=fake_pipe)
    ops = AtomicRedisOperations(redis)

    ok = await ops.atomic_market_data_write("market:1", {"best_bid": 10})

    assert ok is False
    assert fake_pipe.executed is True


@pytest.mark.asyncio
async def test_safe_market_data_read_returns_none_when_fields_missing(monkeypatch):
    monkeypatch.setattr("src.common.redis_protocol.atomic_operations.MAX_READ_RETRIES", 3)
    sleep_mock = AsyncMock()
    monkeypatch.setattr("src.common.redis_protocol.atomic_operations.asyncio.sleep", sleep_mock)

    redis = _RedisStub(hgetall=AsyncMock(return_value={"best_bid": "10", "best_bid_size": "1"}))

    ops = AtomicRedisOperations(redis)
    with pytest.raises(RedisDataValidationError, match="Error reading market data from key"):
        await ops.safe_market_data_read("market:1", required_fields=["best_bid", "best_ask"])
    assert redis.hgetall.await_count == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_safe_market_data_read_rejects_non_positive_prices(monkeypatch):
    monkeypatch.setattr("src.common.redis_protocol.atomic_operations.MAX_READ_RETRIES", 3)
    sleep_mock = AsyncMock()
    monkeypatch.setattr("src.common.redis_protocol.atomic_operations.asyncio.sleep", sleep_mock)

    redis = _RedisStub(
        hgetall=AsyncMock(
            return_value={
                "best_bid": "0",
                "best_ask": "1",
                "best_bid_size": "1",
                "best_ask_size": "1",
            }
        )
    )

    ops = AtomicRedisOperations(redis)
    with pytest.raises(RedisDataValidationError, match="Error reading market data from key"):
        await ops.safe_market_data_read("market:1")
    assert redis.hgetall.await_count == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_safe_market_data_read_handles_exceptions(monkeypatch):
    monkeypatch.setattr("src.common.redis_protocol.atomic_operations.MAX_READ_RETRIES", 3)
    sleep_mock = AsyncMock()
    monkeypatch.setattr("src.common.redis_protocol.atomic_operations.asyncio.sleep", sleep_mock)

    redis = _RedisStub(hgetall=AsyncMock(side_effect=RuntimeError("fail")))

    ops = AtomicRedisOperations(redis)
    with pytest.raises(RedisDataValidationError, match="Error reading market data"):
        await ops.safe_market_data_read("market:1")
    assert redis.hgetall.await_count == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_atomic_delete_if_invalid_keeps_valid_data():
    delete_mock = AsyncMock(return_value=0)
    redis = _RedisStub(delete=delete_mock)
    ops = AtomicRedisOperations(redis)

    deleted = await ops.atomic_delete_if_invalid(
        "market:1",
        {"best_bid": 10, "best_ask": 11, "best_bid_size": 1, "best_ask_size": 1},
    )

    assert deleted is False
    delete_mock.assert_not_awaited()
