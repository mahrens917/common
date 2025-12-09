"""Tests for trade price updater module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.redis_protocol.kalshi_store.orderbook_helpers.trade_price_updater import (
    TradePriceUpdater,
)


class TestTradePriceUpdater:
    """Tests for TradePriceUpdater class."""

    @pytest.mark.asyncio
    async def test_updates_prices_when_both_present(self) -> None:
        """Updates prices when both bid and ask are present."""
        callback = AsyncMock()
        updater = TradePriceUpdater(callback)
        redis = AsyncMock()
        redis.hget = AsyncMock(side_effect=[b"50", b"55"])

        await updater.update_trade_prices(redis, "market:key", "TICKER")

        callback.assert_called_once_with("TICKER", 50, 55)

    @pytest.mark.asyncio
    async def test_does_not_update_when_bid_missing(self) -> None:
        """Does not update when bid is None."""
        callback = AsyncMock()
        updater = TradePriceUpdater(callback)
        redis = AsyncMock()
        redis.hget = AsyncMock(side_effect=[None, b"55"])

        await updater.update_trade_prices(redis, "market:key", "TICKER")

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_update_when_ask_missing(self) -> None:
        """Does not update when ask is None."""
        callback = AsyncMock()
        updater = TradePriceUpdater(callback)
        redis = AsyncMock()
        redis.hget = AsyncMock(side_effect=[b"50", None])

        await updater.update_trade_prices(redis, "market:key", "TICKER")

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_string_values(self) -> None:
        """Handles non-bytes string values."""
        callback = AsyncMock()
        updater = TradePriceUpdater(callback)
        redis = AsyncMock()
        redis.hget = AsyncMock(side_effect=["50", "55"])

        await updater.update_trade_prices(redis, "market:key", "TICKER")

        callback.assert_called_once_with("TICKER", 50, 55)
