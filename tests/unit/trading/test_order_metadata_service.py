"""Tests for order_metadata_service module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.trading.order_metadata_service import fetch_order_metadata
from common.trading_exceptions import KalshiDataIntegrityError


class TestFetchOrderMetadata:
    """Tests for fetch_order_metadata function."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_trade_store(self):
        store = MagicMock()
        store.get_order_metadata = AsyncMock()
        return store

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_success(self, mock_trade_store, mock_logger):
        mock_trade_store.get_order_metadata.return_value = {
            "trade_rule": "weather_high",
            "trade_reason": "temperature exceeded threshold for market",
        }

        async def store_supplier():
            return mock_trade_store

        result = await fetch_order_metadata(
            "order-123",
            store_supplier,
            None,
            mock_logger,
        )

        assert result == ("temperature exceeded threshold for market", "weather_high")

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_missing_metadata(self, mock_trade_store, mock_logger):
        mock_trade_store.get_order_metadata.return_value = None

        async def store_supplier():
            return mock_trade_store

        with pytest.raises(KalshiDataIntegrityError, match="No order metadata found"):
            await fetch_order_metadata(
                "order-missing",
                store_supplier,
                None,
                mock_logger,
            )

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_missing_trade_rule(self, mock_trade_store, mock_logger):
        mock_trade_store.get_order_metadata.return_value = {
            "trade_reason": "some reason",
        }

        async def store_supplier():
            return mock_trade_store

        with pytest.raises(KalshiDataIntegrityError, match="No order metadata found"):
            await fetch_order_metadata(
                "order-partial",
                store_supplier,
                None,
                mock_logger,
            )

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_missing_trade_reason(self, mock_trade_store, mock_logger):
        mock_trade_store.get_order_metadata.return_value = {
            "trade_rule": "some rule",
        }

        async def store_supplier():
            return mock_trade_store

        with pytest.raises(KalshiDataIntegrityError, match="No order metadata found"):
            await fetch_order_metadata(
                "order-partial",
                store_supplier,
                None,
                mock_logger,
            )

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_invalid_trade_reason(self, mock_trade_store, mock_logger):
        mock_trade_store.get_order_metadata.return_value = {
            "trade_rule": "weather_rule",
            "trade_reason": "ab",
        }

        async def store_supplier():
            return mock_trade_store

        with pytest.raises(ValueError, match="Trade reason too short"):
            await fetch_order_metadata(
                "order-invalid",
                store_supplier,
                None,
                mock_logger,
            )

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_sends_alert_on_missing(self, mock_trade_store, mock_logger):
        mock_trade_store.get_order_metadata.return_value = None
        mock_telegram = MagicMock()
        mock_telegram.send_alert = AsyncMock()

        async def store_supplier():
            return mock_trade_store

        with pytest.raises(KalshiDataIntegrityError):
            await fetch_order_metadata(
                "order-missing",
                store_supplier,
                mock_telegram,
                mock_logger,
            )

        mock_telegram.send_alert.assert_called_once()
        call_args = mock_telegram.send_alert.call_args[0][0]
        assert "ORDER METADATA MISSING" in call_args

    @pytest.mark.asyncio
    async def test_fetch_order_metadata_handles_alert_failure(self, mock_trade_store, mock_logger):
        mock_trade_store.get_order_metadata.return_value = None
        mock_telegram = MagicMock()
        mock_telegram.send_alert = AsyncMock(side_effect=ConnectionError("Alert failed"))

        async def store_supplier():
            return mock_trade_store

        with pytest.raises(KalshiDataIntegrityError):
            await fetch_order_metadata(
                "order-missing",
                store_supplier,
                mock_telegram,
                mock_logger,
            )

        mock_logger.warning.assert_called()
