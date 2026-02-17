from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import orjson
import pytest

from common.data_models.trade_record import PnLReport, TradeRecord, TradeSide
from common.exceptions import ValidationError
from common.redis_protocol.trade_store import (
    OrderMetadataError,
    TradeStore,
    TradeStoreError,
)

_CONST_75 = 75
_TEST_COUNT_2 = 2
_VAL_70_0 = 70.0
_VAL_80_0 = 80.0

from common.redis_protocol.trade_store.keys import TradeKeyBuilder


def _make_trade(order_id: str = "order-1", **overrides: Any) -> TradeRecord:
    trade_timestamp = datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc)
    payload = {
        "order_id": order_id,
        "market_ticker": "KXHIGHNYC-24JAN02-B100",
        "trade_timestamp": trade_timestamp,
        "trade_side": TradeSide.YES,
        "quantity": 2,
        "price_cents": 60,
        "fee_cents": 5,
        "cost_cents": 125,
        "market_category": "weather",
        "weather_station": "NYC",
        "trade_rule": "rule_3",
        "trade_reason": "Reasonable trade",
    }
    payload.update(overrides)
    return TradeRecord(**payload)


def _build_store(monkeypatch, fake_redis_client_factory):
    fake = fake_redis_client_factory("common.redis_protocol.trade_store.get_redis_pool")
    monkeypatch.setattr(
        "common.redis_protocol.trade_store.load_configured_timezone",
        lambda: "UTC",
        raising=False,
    )
    store = TradeStore(redis=fake)
    store.redis = fake
    store._base_connection.initialized = True  # type: ignore[attr-defined]
    store._connection_mgr.ensure_redis_connection = AsyncMock(return_value=True)
    return store, fake


KEYS = TradeKeyBuilder()


def _trade_key(trade: TradeRecord) -> str:
    return KEYS.trade(trade.trade_timestamp.date(), trade.order_id)


@pytest.mark.asyncio
async def test_store_trade_indexes_record(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade()
    trade.settlement_price_cents = 75
    trade.settlement_time = datetime(2024, 1, 3, tzinfo=timezone.utc)

    stored = await store.store_trade(trade)
    assert stored is True

    trade_key = _trade_key(trade)
    persisted = await fake.get(trade_key)
    record = orjson.loads(persisted)
    assert record["order_id"] == trade.order_id
    assert record["trade_rule"] == trade.trade_rule

    date_key = KEYS.date_index(trade.trade_timestamp.date())
    assert fake.dump_set(date_key) == {trade.order_id}
    assert fake.dump_set(KEYS.station(trade.weather_station)) == {trade.order_id}
    assert fake.dump_set(KEYS.rule(trade.trade_rule)) == {trade.order_id}
    assert fake.dump_set(KEYS.category("weather")) == {trade.order_id}


@pytest.mark.asyncio
async def test_store_trade_supports_non_weather(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(
        order_id="crypto-order",
        market_ticker="KXBTCJAN25-100",
        market_category="binary",
        weather_station=None,
        trade_rule="EMERGENCY_EXIT",
        trade_reason="Emergency exit rule",
    )

    stored = await store.store_trade(trade)
    assert stored is True

    assert fake.dump_set(KEYS.category("binary")) == {trade.order_id}
    assert fake.dump_set(KEYS.rule(trade.trade_rule)) == {trade.order_id}
    assert fake.dump_set(KEYS.station(str(trade.weather_station))) == set()


@pytest.mark.asyncio
async def test_get_trade_round_trips_data(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade()
    await store.store_trade(trade)

    retrieved = await store.get_trade(trade.trade_timestamp.date(), trade.order_id)
    assert isinstance(retrieved, TradeRecord)
    assert retrieved.order_id == trade.order_id
    assert retrieved.trade_reason == trade.trade_reason

    retrieved_by_id = await store.get_trade_by_order_id(trade.order_id)
    assert retrieved_by_id is not None
    assert retrieved_by_id.trade_rule == trade.trade_rule


@pytest.mark.asyncio
async def test_mark_trade_settled_updates_payload(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade()
    await store.store_trade(trade)

    settled_at = datetime(2024, 1, 3, 9, tzinfo=timezone.utc)
    result = await store.mark_trade_settled(trade.order_id, settlement_price_cents=75, settled_at=settled_at)
    assert result is True

    refreshed = await store.get_trade_by_order_id(trade.order_id)
    assert refreshed is not None
    assert refreshed.settlement_price_cents == _CONST_75
    assert refreshed.settlement_time == settled_at


@pytest.mark.asyncio
async def test_order_metadata_helpers(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    metadata_saved = await store.store_order_metadata("order-meta", "rule_4", "Valid reason 123")
    assert metadata_saved is True

    metadata = await store.get_order_metadata("order-meta")
    assert metadata == {
        "trade_rule": "rule_4",
        "trade_reason": "Valid reason 123",
        "market_category": "weather",
    }


@pytest.mark.asyncio
async def test_order_metadata_with_optional_fields(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    metadata_saved = await store.store_order_metadata(
        "order-binary",
        "EMERGENCY_EXIT",
        "Emergency exit rule",
        market_category="binary",
    )
    assert metadata_saved is True

    metadata = await store.get_order_metadata("order-binary")
    assert metadata["trade_rule"] == "EMERGENCY_EXIT"
    assert metadata["trade_reason"] == "Emergency exit rule"
    assert metadata["market_category"] == "binary"
    assert "weather_station" not in metadata


@pytest.mark.asyncio
async def test_get_trade_by_order_id_raises_on_invalid_payload(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade()
    await store.store_trade(trade)

    trade_key = _trade_key(trade)
    raw = await fake.get(trade_key)
    payload = orjson.loads(raw)
    payload["trade_reason"] = "short"  # violates validation in retrieval path
    await fake.set(trade_key, orjson.dumps(payload).decode("utf-8"))

    with pytest.raises(TradeStoreError, match="get_trade_by_order_id failed"):
        await store.get_trade_by_order_id(trade.order_id)


@pytest.mark.asyncio
async def test_store_order_metadata_rejects_short_reason(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)

    with pytest.raises(OrderMetadataError, match="too short"):
        await store.store_order_metadata("order-short", "rule_3", "too-short")
    metadata_key = KEYS.order_metadata("order-short")
    assert await fake.get(metadata_key) is None


@pytest.mark.asyncio
async def test_store_order_metadata_rejects_empty_reason(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    with pytest.raises(OrderMetadataError, match="Empty trade_reason"):
        await store.store_order_metadata("order-empty-reason", "rule_3", "")


@pytest.mark.asyncio
async def test_mark_trade_settled_returns_false_when_order_missing(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    with pytest.raises(TradeStoreError, match="not indexed"):
        await store.mark_trade_settled("missing-order", settlement_price_cents=80)


@pytest.mark.asyncio
async def test_get_order_metadata_handles_invalid_json(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    metadata_key = KEYS.order_metadata("order-corrupt")
    await fake.set(metadata_key, "not-json")

    with pytest.raises(OrderMetadataError, match="not valid JSON"):
        await store.get_order_metadata("order-corrupt")


@pytest.mark.asyncio
async def test_mark_trade_settled_handles_exception(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._repository._redis_provider = AsyncMock(side_effect=RuntimeError("mark error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="mark_trade_settled failed"):
        await store.mark_trade_settled("order", settlement_price_cents=90)


@pytest.mark.asyncio
async def test_get_trade_converts_naive_datetimes(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="naive")
    trade.trade_timestamp = datetime(2024, 1, 2, 15, 30)
    trade.settlement_time = datetime(2024, 1, 3, 11, 0)
    trade.settlement_price_cents = 70
    await store.store_trade(trade)

    key = _trade_key(trade)
    payload = orjson.loads(await fake.get(key))
    payload["last_price_update"] = "2024-01-02T15:45:00"
    await fake.set(key, orjson.dumps(payload).decode("utf-8"))

    retrieved = await store.get_trade(trade.trade_timestamp.date(), trade.order_id)
    assert retrieved.trade_timestamp.tzinfo == timezone.utc
    assert retrieved.last_price_update.tzinfo == timezone.utc  # type: ignore[union-attr]
    assert retrieved.settlement_time.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_get_trade_by_order_id_raises_on_missing_field(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="missing-field")
    await store.store_trade(trade)

    order_index_key = KEYS.order_index(trade.order_id)
    trade_key = await fake.get(order_index_key)
    payload = orjson.loads(await fake.get(trade_key))
    payload.pop("weather_station")
    await fake.set(trade_key, orjson.dumps(payload).decode("utf-8"))

    with pytest.raises(ValidationError, match="Missing required field"):
        await store.get_trade_by_order_id(trade.order_id)


@pytest.mark.asyncio
async def test_get_trade_by_order_id_raises_on_empty_trade_rule(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="empty-rule")
    await store.store_trade(trade)

    order_index_key = KEYS.order_index(trade.order_id)
    trade_key = await fake.get(order_index_key)
    payload = orjson.loads(await fake.get(trade_key))
    payload["trade_rule"] = ""
    await fake.set(trade_key, orjson.dumps(payload).decode("utf-8"))

    with pytest.raises(TradeStoreError, match="get_trade_by_order_id failed"):
        await store.get_trade_by_order_id(trade.order_id)


@pytest.mark.asyncio
async def test_get_trade_by_order_id_raises_on_empty_trade_reason(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="empty-reason")
    await store.store_trade(trade)

    order_index_key = KEYS.order_index(trade.order_id)
    trade_key = await fake.get(order_index_key)
    payload = orjson.loads(await fake.get(trade_key))
    payload["trade_reason"] = ""
    await fake.set(trade_key, orjson.dumps(payload).decode("utf-8"))

    with pytest.raises(TradeStoreError, match="get_trade_by_order_id failed"):
        await store.get_trade_by_order_id(trade.order_id)


@pytest.mark.asyncio
async def test_store_trade_detects_pipeline_failure(monkeypatch):
    class BrokenPipeline:
        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

        def set(self, *args, **kwargs):
            return self

        def sadd(self, *args, **kwargs):
            return self

        async def execute(self):
            return [True, None, True, True, True]

    class BrokenRedis:
        async def ping(self):
            return True

        def pipeline(self):
            return BrokenPipeline()

    store = TradeStore(redis=BrokenRedis())
    store.redis = store.redis
    store._base_connection.initialized = True  # type: ignore[attr-defined]
    store._connection_mgr.ensure_redis_connection = AsyncMock(return_value=True)

    with pytest.raises(TradeStoreError, match="Redis pipeline operations failed"):
        await store.store_trade(_make_trade())


@pytest.mark.asyncio
async def test_mark_trade_settled_returns_false_when_trade_missing(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    order_index_key = KEYS.order_index("missing-order")
    await fake.set(order_index_key, "trades:2024-01-02:missing-order")

    with pytest.raises(TradeStoreError, match="missing for order"):
        await store.mark_trade_settled("missing-order", settlement_price_cents=90)


@pytest.mark.asyncio
async def test_get_trade_returns_none_when_missing(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    result = await store.get_trade(date(2024, 1, 2), "unknown")

    assert result is None


@pytest.mark.asyncio
async def test_get_trade_raises_on_missing_field(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade()
    await store.store_trade(trade)

    key = _trade_key(trade)
    payload = orjson.loads(await fake.get(key))
    payload.pop("fee_cents", None)
    await fake.set(key, orjson.dumps(payload).decode("utf-8"))

    with pytest.raises(ValidationError, match="Missing required field"):
        await store.get_trade(trade.trade_timestamp.date(), trade.order_id)


@pytest.mark.asyncio
async def test_get_trade_by_order_id_returns_none_when_not_indexed(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    result = await store.get_trade_by_order_id("unknown")
    assert result is None


@pytest.mark.asyncio
async def test_get_trade_by_order_id_returns_none_when_trade_missing(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade()
    await store.store_trade(trade)

    order_index_key = KEYS.order_index(trade.order_id)
    await fake.set(order_index_key, "trades:2099-01-01:missing")

    with pytest.raises(TradeStoreError, match="payload missing"):
        await store.get_trade_by_order_id(trade.order_id)


@pytest.mark.asyncio
async def test_get_trade_by_order_id_converts_naive_datetimes(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="naive-order")
    trade.trade_timestamp = datetime(2024, 1, 2, 15, 30)
    trade.settlement_time = datetime(2024, 1, 3, 10, 0)
    trade.settlement_price_cents = 60
    await store.store_trade(trade)

    order_index_key = KEYS.order_index(trade.order_id)
    trade_key = await fake.get(order_index_key)
    payload = orjson.loads(await fake.get(trade_key))
    payload["last_price_update"] = "2024-01-02T16:00:00"
    await fake.set(trade_key, orjson.dumps(payload).decode("utf-8"))

    retrieved = await store.get_trade_by_order_id(trade.order_id)
    assert retrieved.trade_timestamp.tzinfo == timezone.utc
    assert retrieved.last_price_update.tzinfo == timezone.utc  # type: ignore[union-attr]
    assert retrieved.settlement_time.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_store_order_metadata_rejects_empty_rule(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    with pytest.raises(OrderMetadataError, match="Empty trade_rule"):
        await store.store_order_metadata("order-empty", "", "Valid reason 123")


@pytest.mark.asyncio
async def test_get_order_metadata_missing_required_fields(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    metadata_key = KEYS.order_metadata("order-invalid")
    await fake.set(metadata_key, orjson.dumps({"trade_rule": "rule_3"}).decode("utf-8"))

    with pytest.raises(OrderMetadataError, match="missing required fields"):
        await store.get_order_metadata("order-invalid")


@pytest.mark.asyncio
async def test_get_order_metadata_returns_none_when_missing(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    metadata = await store.get_order_metadata("no-metadata")
    assert metadata is None


@pytest.mark.asyncio
async def test_initialize_and_close(monkeypatch, fake_redis_client_factory):
    fake = fake_redis_client_factory("common.redis_protocol.trade_store.get_redis_pool")
    store = TradeStore()
    store._connection_mgr.ensure_redis_connection = AsyncMock(return_value=True)

    result = await store.initialize()
    assert result is True

    store.redis = fake
    await store.close()
    assert store.redis is None


@pytest.mark.asyncio
async def test_get_redis_raises_when_connection_unavailable(monkeypatch):
    store = TradeStore()
    store._connection_mgr.ensure_redis_connection = AsyncMock(return_value=False)

    with pytest.raises(TradeStoreError, match="Failed to establish Redis connection"):
        await store._get_redis()


@pytest.mark.asyncio
async def test_get_redis_raises_when_connection_missing_after_init(monkeypatch):
    store = TradeStore()

    async def fake_ensure():
        if not hasattr(fake_ensure, "calls"):
            fake_ensure.calls = 0
        fake_ensure.calls += 1
        store._base_connection.initialized = True  # type: ignore[attr-defined]
        store.redis = None
        return fake_ensure.calls == 1

    store._connection_mgr.ensure_redis_connection = AsyncMock(side_effect=fake_ensure)

    with pytest.raises(TradeStoreError, match="Failed to re-establish Redis connection"):
        await store._get_redis()


@pytest.mark.asyncio
async def test_get_redis_retries_and_raises_on_ping_failure(monkeypatch):
    class TimeoutRedis:
        async def ping(self):
            raise asyncio.TimeoutError()

    store = TradeStore(redis=TimeoutRedis())
    store.redis = store.redis
    store._base_connection.initialized = True  # type: ignore[attr-defined]
    store._connection_mgr.ensure_redis_connection = AsyncMock(return_value=False)

    with pytest.raises(TradeStoreError, match="Failed to re-establish"):
        await store._get_redis()


@pytest.mark.asyncio
async def test_close_handles_close_errors(monkeypatch):
    class BadRedis:
        async def close(self):
            raise RuntimeError("close error")

    store = TradeStore(redis=BadRedis())
    store.redis = store.redis
    store._base_connection.initialized = True  # type: ignore[attr-defined]

    await store.close()
    assert store.redis is None


@pytest.mark.asyncio
async def test_get_trades_by_date_range_respects_historical_start(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._queries._start_date_loader = lambda: date(2024, 1, 3)  # type: ignore[attr-defined]

    trades = await store.get_trades_by_date_range(date(2024, 1, 1), date(2024, 1, 2))
    assert trades == []


@pytest.mark.asyncio
async def test_get_trades_by_date_range_multiple_days(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    trade1 = _make_trade(order_id="order-a")
    trade2 = _make_trade(order_id="order-b")
    trade2.trade_timestamp = trade2.trade_timestamp + timedelta(days=1)

    await store.store_trade(trade1)
    await store.store_trade(trade2)

    store._queries._start_date_loader = lambda: date(2024, 1, 1)  # type: ignore[attr-defined]

    trades = await store.get_trades_by_date_range(date(2024, 1, 1), date(2024, 1, 5))
    assert {t.order_id for t in trades} == {"order-a", "order-b"}


@pytest.mark.asyncio
async def test_get_trades_by_date_range_propagates_errors(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    await store.store_trade(_make_trade())

    store._repository.get = AsyncMock(side_effect=TradeStoreError("fetch fail"))  # type: ignore[attr-defined]

    store._queries._start_date_loader = lambda: date(2024, 1, 1)  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="fetch fail"):
        await store.get_trades_by_date_range(date(2024, 1, 2), date(2024, 1, 2))


@pytest.mark.asyncio
async def test_get_trades_by_date_range_clamps_start_before_history(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    store._queries._start_date_loader = lambda: date(2024, 1, 5)  # type: ignore[attr-defined]

    result = await store.get_trades_by_date_range(date(2024, 1, 4), date(2024, 1, 6))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_trades_by_date_range_end_before_start_returns_empty(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    store._queries._start_date_loader = lambda: date(2024, 1, 5)  # type: ignore[attr-defined]

    result = await store.get_trades_by_date_range(date(2024, 1, 5), date(2024, 1, 4))
    assert result == []


@pytest.mark.asyncio
async def test_get_trades_by_station_returns_results(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="station-order")
    trade.trade_timestamp = datetime.now(timezone.utc)
    await store.store_trade(trade)

    trades = await store.get_trades_by_station(trade.weather_station)
    assert trades and trades[0].order_id == "station-order"


@pytest.mark.asyncio
async def test_get_trades_by_station_handles_errors(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._repository._redis_provider = AsyncMock(side_effect=RuntimeError("station error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="get_trades_by_station failed"):
        await store.get_trades_by_station("NYC")


@pytest.mark.asyncio
async def test_get_trades_by_rule_returns_results(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="rule-order")
    trade.trade_timestamp = datetime.now(timezone.utc)
    await store.store_trade(trade)

    trades = await store.get_trades_by_rule(trade.trade_rule)
    assert trades and trades[0].order_id == "rule-order"


@pytest.mark.asyncio
async def test_get_trades_by_rule_handles_errors(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._repository._redis_provider = AsyncMock(side_effect=RuntimeError("rule error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="get_trades_by_rule failed"):
        await store.get_trades_by_rule("rule_3")


@pytest.mark.asyncio
async def test_store_and_get_daily_summary(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    summary = PnLReport(
        report_date=date(2024, 1, 5),
        start_date=date(2024, 1, 5),
        end_date=date(2024, 1, 5),
        total_trades=1,
        total_cost_cents=100,
        total_pnl_cents=50,
        win_rate=1.0,
        by_weather_station={},
        by_rule={},
    )

    stored = await store.store_daily_summary(summary)
    assert stored is True

    fetched = await store.get_daily_summary(summary.report_date)
    assert fetched["total_trades"] == 1


@pytest.mark.asyncio
async def test_store_daily_summary_handles_error(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._pnl._redis_provider = AsyncMock(side_effect=RuntimeError("summary error"))  # type: ignore[attr-defined]

    summary = PnLReport(
        report_date=date(2024, 1, 6),
        start_date=date(2024, 1, 6),
        end_date=date(2024, 1, 6),
        total_trades=0,
        total_cost_cents=0,
        total_pnl_cents=0,
        win_rate=0.0,
        by_weather_station={},
        by_rule={},
    )

    with pytest.raises(TradeStoreError, match="store_daily_summary failed"):
        await store.store_daily_summary(summary)


@pytest.mark.asyncio
async def test_get_daily_summary_returns_none_when_missing(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    summary = await store.get_daily_summary(date(2024, 1, 7))
    assert summary is None


@pytest.mark.asyncio
async def test_get_daily_summary_handles_error(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._pnl._redis_provider = AsyncMock(side_effect=RuntimeError("summary read error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="get_daily_summary failed"):
        await store.get_daily_summary(date(2024, 1, 7))


@pytest.mark.asyncio
async def test_get_trades_closed_today_filters(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    today = date(2024, 1, 8)
    store._queries._timezone_aware_date = lambda tz: today  # type: ignore[attr-defined]
    store._queries._start_date_loader = lambda: today - timedelta(days=5)  # type: ignore[attr-defined]

    trade_today = _make_trade(order_id="today")
    trade_today.trade_timestamp = datetime(2024, 1, 8, 9, tzinfo=timezone.utc)
    trade_today.settlement_time = datetime(2024, 1, 8, 10, tzinfo=timezone.utc)
    trade_yesterday = _make_trade(order_id="yesterday")
    trade_yesterday.trade_timestamp = datetime(2024, 1, 7, 11, tzinfo=timezone.utc)
    trade_yesterday.settlement_time = datetime(2024, 1, 7, 12, tzinfo=timezone.utc)

    await store.store_trade(trade_today)
    await store.store_trade(trade_yesterday)

    trades = await store.get_trades_closed_today()
    assert [t.order_id for t in trades] == ["today"]


@pytest.mark.asyncio
async def test_get_trades_closed_today_raises(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._queries.trades_closed_today = AsyncMock(side_effect=TradeStoreError("closed today error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="closed today error"):
        await store.get_trades_closed_today()


@pytest.mark.asyncio
async def test_get_trades_closed_yesterday_filters(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    today = date(2024, 1, 9)
    store._queries._timezone_aware_date = lambda tz: today  # type: ignore[attr-defined]
    store._queries._start_date_loader = lambda: today - timedelta(days=5)  # type: ignore[attr-defined]

    trade_today = _make_trade(order_id="today-close")
    trade_today.trade_timestamp = datetime(2024, 1, 9, 9, tzinfo=timezone.utc)
    trade_today.settlement_time = datetime(2024, 1, 9, 10, tzinfo=timezone.utc)
    trade_yesterday = _make_trade(order_id="yesterday-close")
    trade_yesterday.trade_timestamp = datetime(2024, 1, 8, 9, tzinfo=timezone.utc)
    trade_yesterday.settlement_time = datetime(2024, 1, 8, 12, tzinfo=timezone.utc)
    trade_old = _make_trade(order_id="older")
    trade_old.trade_timestamp = datetime(2024, 1, 7, 9, tzinfo=timezone.utc)
    trade_old.settlement_time = datetime(2024, 1, 7, 12, tzinfo=timezone.utc)

    await store.store_trade(trade_today)
    await store.store_trade(trade_yesterday)
    await store.store_trade(trade_old)

    trades = await store.get_trades_closed_yesterday()
    assert [t.order_id for t in trades] == ["yesterday-close"]


@pytest.mark.asyncio
async def test_get_trades_closed_yesterday_raises(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._queries.trades_closed_yesterday = AsyncMock(side_effect=TradeStoreError("closed yesterday error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="closed yesterday error"):
        await store.get_trades_closed_yesterday()


@pytest.mark.asyncio
async def test_get_unrealized_trades_for_date(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="unrealized")
    store._queries.trades_by_date_range = AsyncMock(return_value=[trade])  # type: ignore[attr-defined]

    trades = await store.get_unrealized_trades_for_date(date(2024, 1, 10))
    assert [t.order_id for t in trades] == ["unrealized"]


@pytest.mark.asyncio
async def test_get_unrealized_trades_for_date_raises(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._queries.trades_by_date_range = AsyncMock(side_effect=TradeStoreError("unrealized error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="unrealized error"):
        await store.get_unrealized_trades_for_date(date(2024, 1, 11))


@pytest.mark.asyncio
async def test_store_and_get_unrealized_pnl_data(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    data = {"value": 123}

    saved = await store.store_unrealized_pnl_data("pnl:key", data)
    assert saved is True

    retrieved = await store.get_unrealized_pnl_data("pnl:key")
    assert retrieved == data


@pytest.mark.asyncio
async def test_store_unrealized_pnl_data_handles_error(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._pnl._redis_provider = AsyncMock(side_effect=RuntimeError("unrealized store error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="store_unrealized_pnl_data failed"):
        await store.store_unrealized_pnl_data("pnl:error", {"value": 1})


@pytest.mark.asyncio
async def test_get_unrealized_pnl_data_returns_none_when_missing(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)

    data = await store.get_unrealized_pnl_data("pnl:missing")
    assert data is None


@pytest.mark.asyncio
async def test_get_unrealized_pnl_data_handles_error(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._pnl._redis_provider = AsyncMock(side_effect=RuntimeError("unrealized read error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="get_unrealized_pnl_data failed"):
        await store.get_unrealized_pnl_data("pnl:error")


@pytest.mark.asyncio
async def test_get_unrealized_pnl_history(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    await fake.set(KEYS.unrealized_pnl(date(2024, 1, 12)), orjson.dumps({"value": 1}).decode("utf-8"))
    await fake.set(KEYS.unrealized_pnl(date(2024, 1, 13)), orjson.dumps({"value": 2}).decode("utf-8"))

    history = await store.get_unrealized_pnl_history(date(2024, 1, 12), date(2024, 1, 13))
    assert len(history) == _TEST_COUNT_2


@pytest.mark.asyncio
async def test_get_unrealized_pnl_history_handles_errors(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._pnl._redis_provider = AsyncMock(side_effect=RuntimeError("history error"))  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="get_unrealized_pnl_history failed"):
        await store.get_unrealized_pnl_history(date(2024, 1, 12), date(2024, 1, 13))


@pytest.mark.asyncio
async def test_update_trade_prices_updates_records(monkeypatch, fake_redis_client_factory):
    store, fake = _build_store(monkeypatch, fake_redis_client_factory)
    trade = _make_trade(order_id="price-order")
    trade.trade_timestamp = datetime(2024, 1, 14, tzinfo=timezone.utc)
    await store.store_trade(trade)

    store._price_updater._timezone_date = lambda tz: date(2024, 1, 14)  # type: ignore[attr-defined]

    updated = await store.update_trade_prices(trade.market_ticker, yes_bid=70.0, yes_ask=80.0)
    assert updated == 1

    trade_key = _trade_key(trade)
    payload = orjson.loads(await fake.get(trade_key))
    assert payload["last_yes_bid"] == _VAL_70_0
    assert payload["last_yes_ask"] == _VAL_80_0


@pytest.mark.asyncio
async def test_update_trade_prices_raises_on_error(monkeypatch, fake_redis_client_factory):
    store, _ = _build_store(monkeypatch, fake_redis_client_factory)
    store._repository._redis_provider = AsyncMock(side_effect=RuntimeError("price error"))  # type: ignore[attr-defined]
    store._price_updater._timezone_date = lambda tz: date(2024, 1, 14)  # type: ignore[attr-defined]

    with pytest.raises(TradeStoreError, match="update_trade_prices failed"):
        await store.update_trade_prices("KXHIGHNYC-24JAN02-B100", 70.0, 80.0)
