"""Tests for best price updater module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.redis_protocol.kalshi_store.orderbook_helpers.best_price_updater import (
    BestPriceUpdater,
)


class TestBestPriceUpdater:
    """Tests for BestPriceUpdater class."""

    @pytest.mark.asyncio
    async def test_store_optional_field_with_value(self) -> None:
        """Stores field when value is present."""
        redis = AsyncMock()

        await BestPriceUpdater.store_optional_field(redis, "market:key", "yes_bid", 50)

        redis.hset.assert_called_once_with("market:key", "yes_bid", "50")

    @pytest.mark.asyncio
    async def test_store_optional_field_deletes_when_none(self) -> None:
        """Deletes field when value is None."""
        redis = AsyncMock()

        await BestPriceUpdater.store_optional_field(redis, "market:key", "yes_bid", None)

        redis.hdel.assert_called_once_with("market:key", "yes_bid")
        redis.hset.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_from_side_bids(self) -> None:
        """Updates best bid from yes_bids side data."""
        redis = AsyncMock()
        redis.hget = AsyncMock(return_value=b"[[50, 100], [45, 200]]")

        with patch(
            "src.common.redis_protocol.kalshi_store.orderbook_helpers.best_price_updater.extract_best_bid",
            return_value=(50, 100),
        ):
            await BestPriceUpdater.update_from_side(redis, "market:key", "yes_bids")

        redis.hget.assert_called_once_with("market:key", "yes_bids")

    @pytest.mark.asyncio
    async def test_update_from_side_asks(self) -> None:
        """Updates best ask from yes_asks side data."""
        redis = AsyncMock()
        redis.hget = AsyncMock(return_value=b"[[55, 100], [60, 200]]")

        with patch(
            "src.common.redis_protocol.kalshi_store.orderbook_helpers.best_price_updater.extract_best_ask",
            return_value=(55, 100),
        ):
            await BestPriceUpdater.update_from_side(redis, "market:key", "yes_asks")

        redis.hget.assert_called_once_with("market:key", "yes_asks")
