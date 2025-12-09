"""Tests for storage helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.order_execution.finalizer_helpers.storage import store_trade_record
from src.common.redis_protocol.trade_store import TradeStoreError
from src.common.trading_exceptions import KalshiTradePersistenceError


class TestStoreTradeRecord:
    """Tests for store_trade_record function."""

    @pytest.mark.asyncio
    async def test_stores_trade_successfully(self) -> None:
        """Stores trade in trade store successfully."""
        trade_store = AsyncMock()
        trade_store.store_trade = AsyncMock()

        trade_record = MagicMock()
        trade_record.ticker = "TICKER-123"

        outcome = MagicMock()
        outcome.total_filled = 10

        await store_trade_record(trade_store, trade_record, "order-123", outcome, "test_op")

        trade_store.store_trade.assert_called_once_with(trade_record)

    @pytest.mark.asyncio
    async def test_raises_persistence_error_on_store_failure(self) -> None:
        """Raises KalshiTradePersistenceError when store fails."""
        trade_store = AsyncMock()
        trade_store.store_trade = AsyncMock(side_effect=TradeStoreError("Store failed"))

        trade_record = MagicMock()
        trade_record.ticker = "TICKER-123"

        outcome = MagicMock()
        outcome.total_filled = 10

        with pytest.raises(KalshiTradePersistenceError):
            await store_trade_record(trade_store, trade_record, "order-123", outcome, "test_op")

    @pytest.mark.asyncio
    async def test_error_contains_order_id(self) -> None:
        """Error contains order_id in context."""
        trade_store = AsyncMock()
        trade_store.store_trade = AsyncMock(side_effect=TradeStoreError("Store failed"))

        trade_record = MagicMock()
        trade_record.ticker = "TICKER-123"

        outcome = MagicMock()
        outcome.total_filled = 10

        with pytest.raises(KalshiTradePersistenceError) as exc_info:
            await store_trade_record(trade_store, trade_record, "order-456", outcome, "test_op")

        assert exc_info.value.order_id == "order-456"
