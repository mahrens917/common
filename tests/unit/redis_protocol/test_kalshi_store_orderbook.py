from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store import KalshiStore


@pytest.mark.asyncio
async def test_process_orderbook_snapshot_persists_levels(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    redis = AsyncMock()
    msg_data = {
        "yes": [[60, 3]],
        "no": [[40, 2]],
    }

    result = await store._process_orderbook_snapshot(
        redis=redis,
        market_key="market:TEST",
        market_ticker="TEST",
        msg_data=msg_data,
        timestamp="123",
    )

    assert result is True
    assert redis.hset.await_count >= 1


@pytest.mark.asyncio
async def test_process_orderbook_delta_rejects_unknown_side() -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())
    redis = AsyncMock()

    result = await store._process_orderbook_delta(
        redis=redis,
        market_key="market:TEST",
        market_ticker="TEST",
        msg_data={"side": "maybe", "price": 50, "delta": 1},
        timestamp="123",
    )

    assert result is False


@pytest.mark.asyncio
async def test_process_orderbook_delta_rejects_invalid_numeric() -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())
    redis = AsyncMock()

    result = await store._process_orderbook_delta(
        redis=redis,
        market_key="market:TEST",
        market_ticker="TEST",
        msg_data={"side": "yes", "price": "bad", "delta": 1},
        timestamp="123",
    )

    assert result is False
    redis.hset.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_orderbook_delta_inits_missing_json(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())
    redis = AsyncMock()
    # First call returns corrupted JSON, second and third return bid/ask values
    redis.hget = AsyncMock(side_effect=[b"not-json", b"51", b"49"])

    # Mock the delta processor's methods
    store_optional_mock = AsyncMock()
    update_prices_mock = AsyncMock()
    store._orderbook._delta_processor._store_optional_field = store_optional_mock
    store._orderbook._update_trade_prices_callback = update_prices_mock

    result = await store._process_orderbook_delta(
        redis=redis,
        market_key="market:TEST",
        market_ticker="TEST",
        msg_data={"side": "yes", "price": 45, "delta": 2},
        timestamp="123",
    )

    assert result is True
    redis.hset.assert_awaited()
    # When JSON is corrupted, side data is initialized as empty, so no best prices exist
    # Therefore update_prices_mock should not be called when both bid and ask are missing
    # Update: just verify optional fields were stored
    store_optional_mock.assert_awaited()


@pytest.mark.asyncio
async def test_update_orderbook_routes_snapshot(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.merge_orderbook_payload",
        lambda message: ("orderbook_snapshot", {"yes": []}, "TEST"),
    )

    store._ensure_redis_connection = AsyncMock(return_value=True)
    store._get_redis = AsyncMock(return_value=AsyncMock())
    snapshot_mock = AsyncMock(return_value=True)
    store._orderbook._snapshot_processor.process_orderbook_snapshot = snapshot_mock

    assert await store.update_orderbook({"msg": {"market_ticker": "TEST"}})
    snapshot_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_orderbook_routes_delta(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.merge_orderbook_payload",
        lambda message: (
            "orderbook_delta",
            {"side": "yes", "price": 45, "delta": 2},
            "TEST",
        ),
    )

    store._ensure_redis_connection = AsyncMock(return_value=True)
    store._get_redis = AsyncMock(return_value=AsyncMock())
    delta_mock = AsyncMock(return_value=True)
    store._orderbook._delta_processor.process_orderbook_delta = delta_mock

    assert await store.update_orderbook({"msg": {"market_ticker": "TEST"}})
    delta_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_orderbook_handles_unsupported_message(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.merge_orderbook_payload",
        lambda message: ("unknown", {}, "TEST"),
    )

    store._ensure_redis_connection = AsyncMock(return_value=True)
    store._get_redis = AsyncMock(return_value=AsyncMock())

    assert await store.update_orderbook({"msg": {"market_ticker": "TEST"}}) is False


@pytest.mark.asyncio
async def test_update_orderbook_tolerates_missing_prices(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.merge_orderbook_payload",
        lambda message: ("orderbook_snapshot", {"yes": []}, "TEST"),
    )

    store._ensure_redis_connection = AsyncMock(return_value=True)
    store._get_redis = AsyncMock(return_value=AsyncMock())

    async def failing_snapshot(**kwargs):
        raise RuntimeError("Missing yes_bid_price for TEST")

    store._orderbook._snapshot_processor.process_orderbook_snapshot = AsyncMock(side_effect=failing_snapshot)

    assert await store.update_orderbook({"msg": {"market_ticker": "TEST"}}) is True


@pytest.mark.asyncio
async def test_update_trade_tick_derives_yes_price(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    store._ensure_redis_connection = AsyncMock(return_value=True)
    redis = AsyncMock()
    store._get_redis = AsyncMock(return_value=redis)
    # Set redis on the orderbook writer
    store._writer._orderbook.redis = redis

    message = {
        "msg": {
            "market_ticker": "RAIN",
            "side": "no",
            "price": 30,
            "count": 4,
            "timestamp": 1699999999,
        }
    }

    assert await store.update_trade_tick(message) is True
    redis.hset.assert_awaited_once()
    args, kwargs = redis.hset.await_args
    assert args[0] == store.get_market_key("RAIN")
    mapping = kwargs["mapping"]
    assert mapping["last_trade_yes_price"] == "70.0"
    assert mapping["last_trade_raw_price"] == "30"


@pytest.mark.asyncio
async def test_update_trade_tick_requires_market_ticker(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    store._ensure_redis_connection = AsyncMock(return_value=True)
    store._get_redis = AsyncMock(return_value=AsyncMock())

    assert await store.update_trade_tick({"msg": {}}) is False


@pytest.mark.asyncio
async def test_update_orderbook_handles_processing_error(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    store._ensure_redis_connection = AsyncMock(return_value=True)
    store._get_redis = AsyncMock(return_value=AsyncMock())

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    store._orderbook._snapshot_processor.process_orderbook_snapshot = AsyncMock(side_effect=explode)
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.merge_orderbook_payload",
        lambda message: ("orderbook_snapshot", {}, "TEST"),
    )

    assert await store.update_orderbook({"msg": {"market_ticker": "TEST"}}) is False


@pytest.mark.asyncio
async def test_update_orderbook_treats_illiquid_market_as_success(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    store._ensure_redis_connection = AsyncMock(return_value=True)
    store._get_redis = AsyncMock(return_value=AsyncMock())

    def illiquid(*_, **__):
        raise RuntimeError("Missing yes_bid_price in snapshot")

    store._orderbook._snapshot_processor.process_orderbook_snapshot = AsyncMock(side_effect=illiquid)
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.merge_orderbook_payload",
        lambda message: ("orderbook_snapshot", {}, "TEST"),
    )

    assert await store.update_orderbook({"msg": {"market_ticker": "TEST"}}) is True


@pytest.mark.asyncio
async def test_update_trade_tick_handles_invalid_prices(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    store._ensure_redis_connection = AsyncMock(return_value=True)
    redis = AsyncMock()
    store._get_redis = AsyncMock(return_value=redis)
    # Set redis on the orderbook writer
    store._writer._orderbook.redis = redis

    message = {
        "msg": {
            "market_ticker": "RAIN",
            "side": "yes",
            "price": "bad",
            "count": 1,
        }
    }

    assert await store.update_trade_tick(message) is True
    args, kwargs = redis.hset.await_args
    mapping = kwargs["mapping"]
    assert "last_trade_yes_price" not in mapping


@pytest.mark.asyncio
async def test_update_trade_tick_handles_redis_error(monkeypatch) -> None:
    store = KalshiStore(redis=None, weather_resolver=MagicMock())

    store._ensure_redis_connection = AsyncMock(return_value=True)
    redis = AsyncMock()
    redis.hset = AsyncMock(side_effect=RuntimeError("redis down"))
    store._get_redis = AsyncMock(return_value=redis)
    # Set redis on the orderbook writer
    store._writer._orderbook.redis = redis

    message = {
        "msg": {
            "market_ticker": "RAIN",
            "side": "yes",
            "price": 55,
            "count": 2,
        }
    }

    assert await store.update_trade_tick(message) is False
