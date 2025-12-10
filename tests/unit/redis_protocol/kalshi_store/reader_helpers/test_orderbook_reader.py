"""Tests for Kalshi store orderbook reader helpers."""

from __future__ import annotations

import logging
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.exceptions import DataError
from common.redis_protocol.kalshi_store.reader_helpers import (
    orderbook_parser,
    orderbook_reader,
)

LOGGER = logging.getLogger(__name__)


class DummyPipeline:
    def __init__(self, results: list[bytes]):
        self._results = results

    def hget(self, *args: Any, **kwargs: Any):
        return self

    async def execute(self):
        return self._results


@pytest.mark.asyncio
async def test_get_orderbook_success(monkeypatch):
    redis = MagicMock()
    results = [b'{"bid": 1}', b'{"ask": 2}']
    redis.pipeline.return_value = DummyPipeline(results)

    parsed: list[tuple[bytes, str, str]] = []

    def fake_parse(payload: bytes, field: str, ticker: str) -> Dict[str, Any]:
        parsed.append((payload, field, ticker))
        return {field: ticker}

    monkeypatch.setattr(orderbook_reader, "parse_orderbook_json", fake_parse)

    reader = orderbook_reader.OrderbookReader(LOGGER)
    data = await reader.get_orderbook(redis, "market:key", "KXHIGHTEST")

    assert data["yes_bids"]["yes_bids"] == "KXHIGHTEST"
    assert data["yes_asks"]["yes_asks"] == "KXHIGHTEST"
    assert parsed[0][1] == "yes_bids"
    assert parsed[1][1] == "yes_asks"


@pytest.mark.asyncio
async def test_get_orderbook_handles_redis_error(monkeypatch):
    redis = MagicMock()
    pipeline = MagicMock()
    pipeline.hget.return_value = pipeline
    execute = AsyncMock(side_effect=RuntimeError("boom"))
    pipeline.execute = execute
    redis.pipeline.return_value = pipeline

    reader = orderbook_reader.OrderbookReader(LOGGER)
    result = await reader.get_orderbook(redis, "market:key", "KXHIGHTEST")

    assert result == {}
    execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_orderbook_side_handles_errors(monkeypatch):
    redis = MagicMock()
    redis.hget = AsyncMock(side_effect=RuntimeError("boom"))
    reader = orderbook_reader.OrderbookReader(LOGGER)

    result = await reader.get_orderbook_side(redis, "market:key", "KXHIGHTEST", "yes_bids")

    assert result == {}


def test_extract_orderbook_sizes_success(monkeypatch):
    monkeypatch.setattr(
        "common.orderbook_utils.extract_best_bid_ask",
        lambda data: (1.0, 2.0),
    )
    payload = {
        "orderbook": '{"yes_bids": {"1": "10"}, "yes_asks": {"2": "20"}}',
    }

    sizes = orderbook_parser.extract_orderbook_sizes("KXHIGHTEST", payload)

    assert sizes == (10.0, 20.0)


def test_extract_orderbook_sizes_missing_orderbook():
    with pytest.raises(DataError):
        orderbook_parser.extract_orderbook_sizes("KXHIGHTEST", {})


def test_extract_orderbook_sizes_actor_returns_non_dict(monkeypatch):
    monkeypatch.setattr(
        "common.orderbook_utils.extract_best_bid_ask",
        lambda data: (1.0, 2.0),
    )
    monkeypatch.setattr(
        orderbook_parser,
        "safe_orjson_loads",
        lambda data, default=None: "not-a-dict",
    )

    with pytest.raises(TypeError):
        orderbook_parser.extract_orderbook_sizes("KXHIGHTEST", {"orderbook": "x"})


def test_extract_orderbook_sizes_missing_price(monkeypatch):
    monkeypatch.setattr(
        "common.orderbook_utils.extract_best_bid_ask",
        lambda data: (1.0, 2.0),
    )
    monkeypatch.setattr(
        orderbook_parser,
        "safe_orjson_loads",
        lambda data, default=None: {"yes_bids": {}, "yes_asks": {}},
    )

    with pytest.raises(RuntimeError):
        orderbook_parser.extract_orderbook_sizes("KXHIGHTEST", {"orderbook": "x"})


def test_parse_orderbook_json_warns_on_empty(monkeypatch):
    monkeypatch.setattr(
        orderbook_parser,
        "safe_orjson_loads",
        lambda data, default=None: {},
    )

    result = orderbook_parser.parse_orderbook_json(b'{"key":1}', "yes_bids", "KXHIGHTEST")

    assert result == {}
