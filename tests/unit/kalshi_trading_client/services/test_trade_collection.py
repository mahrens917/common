"""Tests for trade_collection module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.exceptions import ValidationError
from common.kalshi_trading_client.services.trade_collection import TradeCollectionController


class TestTradeCollectionController:
    """Tests for TradeCollectionController class."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_trade_store(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_start_success(self, mock_trade_store, mock_logger):
        async def store_getter():
            return mock_trade_store

        controller = TradeCollectionController(
            trade_store_getter=store_getter,
            logger=mock_logger,
        )

        await controller.start()

        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_start_raises_on_runtime_error(self, mock_logger):
        async def store_getter():
            raise RuntimeError("Store not initialized")

        controller = TradeCollectionController(
            trade_store_getter=store_getter,
            logger=mock_logger,
        )

        with pytest.raises(ValidationError, match="Trade store required"):
            await controller.start()

    @pytest.mark.asyncio
    async def test_start_raises_on_value_error(self, mock_logger):
        async def store_getter():
            raise ValueError("Invalid configuration")

        controller = TradeCollectionController(
            trade_store_getter=store_getter,
            logger=mock_logger,
        )

        with pytest.raises(ValidationError, match="Trade store required"):
            await controller.start()

    @pytest.mark.asyncio
    async def test_start_raises_on_type_error(self, mock_logger):
        async def store_getter():
            raise TypeError("Type mismatch")

        controller = TradeCollectionController(
            trade_store_getter=store_getter,
            logger=mock_logger,
        )

        with pytest.raises(ValidationError, match="Trade store required"):
            await controller.start()

    @pytest.mark.asyncio
    async def test_start_raises_on_attribute_error(self, mock_logger):
        async def store_getter():
            raise AttributeError("Missing attribute")

        controller = TradeCollectionController(
            trade_store_getter=store_getter,
            logger=mock_logger,
        )

        with pytest.raises(ValidationError, match="Trade store required"):
            await controller.start()

    @pytest.mark.asyncio
    async def test_stop_logs_message(self, mock_trade_store, mock_logger):
        async def store_getter():
            return mock_trade_store

        controller = TradeCollectionController(
            trade_store_getter=store_getter,
            logger=mock_logger,
        )

        await controller.stop()

        mock_logger.info.assert_called_with("[KalshiTradingClient] Trade collection stopped")
