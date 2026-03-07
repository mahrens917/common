"""Tests for TradeRecordRepository data access methods."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from common.data_models.trade_record import TradeRecord, TradeSide
from common.redis_protocol.trade_store.codec import TradeRecordCodec
from common.redis_protocol.trade_store.errors import TradeStoreError
from common.redis_protocol.trade_store.keys import TradeKeyBuilder
from common.redis_protocol.trade_store.records import TradeRecordRepository

_KEYS = TradeKeyBuilder()
_CODEC = TradeRecordCodec()
_LOGGER = logging.getLogger("test")


def _make_repo(fake_redis) -> TradeRecordRepository:
    return TradeRecordRepository(AsyncMock(return_value=fake_redis), key_builder=_KEYS, codec=_CODEC, logger=_LOGGER)


def _make_trade(**overrides: Any) -> TradeRecord:
    payload = {
        "order_id": "order-1",
        "market_ticker": "KXHIGHNYC-24JAN02-B100",
        "trade_timestamp": datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc),
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


@pytest.mark.asyncio
async def test_save_without_reindex(fake_redis_client_factory) -> None:
    fake = fake_redis_client_factory("common.redis_protocol.trade_store.get_redis_pool")
    repo = _make_repo(fake)
    trade = _make_trade()

    await repo.save_without_reindex(trade)

    trade_key = _KEYS.trade(trade.trade_timestamp.date(), trade.order_id)
    persisted = await fake.get(trade_key)
    assert persisted is not None


@pytest.mark.asyncio
async def test_load_trade_payload_raises_when_missing(fake_redis_client_factory) -> None:
    fake = fake_redis_client_factory("common.redis_protocol.trade_store.get_redis_pool")
    repo = _make_repo(fake)

    with pytest.raises(TradeStoreError, match="Trade payload missing"):
        await repo.load_trade_payload("nonexistent:key")


@pytest.mark.asyncio
async def test_load_trade_payload_returns_mapping(fake_redis_client_factory) -> None:
    fake = fake_redis_client_factory("common.redis_protocol.trade_store.get_redis_pool")
    repo = _make_repo(fake)
    trade = _make_trade()

    await repo.save_without_reindex(trade)
    trade_key = _KEYS.trade(trade.trade_timestamp.date(), trade.order_id)
    mapping = await repo.load_trade_payload(trade_key)
    assert mapping["order_id"] == "order-1"
