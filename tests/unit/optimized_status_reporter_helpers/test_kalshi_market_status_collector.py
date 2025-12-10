from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.optimized_status_reporter_helpers.kalshi_market_status_collector import (
    KalshiMarketStatusCollector,
)


class DummyPipeline:
    def __init__(self):
        self.calls = []

    def set(self, key, value):
        self.calls.append((key, value))
        return self

    async def execute(self):
        return True


@pytest.mark.asyncio
async def test_get_kalshi_market_status_caches_client_and_sets_flags(monkeypatch):
    redis_client = MagicMock()
    pipeline = DummyPipeline()
    redis_client.pipeline = MagicMock(return_value=pipeline)

    collector = KalshiMarketStatusCollector(redis_client=redis_client)

    mock_client = AsyncMock()
    mock_client.get_exchange_status = AsyncMock(
        return_value={"exchange_active": True, "trading_active": False}
    )

    async def fake_get_kalshi_client():
        return mock_client

    collector._get_kalshi_client = fake_get_kalshi_client  # type: ignore[assignment]

    status = await collector.get_kalshi_market_status()

    assert status["exchange_active"] is True
    assert status["trading_active"] is False
    assert ("kalshi:exchange_active", "true") in pipeline.calls
    assert ("kalshi:trading_active", "false") in pipeline.calls


@pytest.mark.asyncio
async def test_get_kalshi_client_is_cached():
    collector = KalshiMarketStatusCollector(redis_client=MagicMock())
    client = MagicMock()
    collector._kalshi_client = client

    first = await collector._get_kalshi_client()
    second = await collector._get_kalshi_client()

    assert first is client
    assert second is client
