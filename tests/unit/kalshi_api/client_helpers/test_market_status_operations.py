"""Tests for kalshi_api market_status_operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.kalshi_api.client_helpers.market_status_operations import MarketStatusOperations


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.api_request = AsyncMock(return_value={})
    return client


@pytest.fixture
def market_ops(mock_client):
    return MarketStatusOperations(mock_client)


@pytest.mark.asyncio
async def test_get_exchange_status(market_ops, mock_client):
    with patch("common.kalshi_api.client_helpers.market_status_operations.validate_exchange_status_response") as mock_validate:
        mock_validate.return_value = {"exchange_active": True, "trading_active": True}

        result = await market_ops.get_exchange_status()

        mock_client.api_request.assert_called_once_with(
            method="GET",
            path="/trade-api/v2/exchange/status",
            params={},
            operation_name="get_exchange_status",
        )
        assert result == {"exchange_active": True, "trading_active": True}


@pytest.mark.asyncio
async def test_is_market_open_true(market_ops, mock_client):
    with patch("common.kalshi_api.client_helpers.market_status_operations.validate_exchange_status_response") as mock_validate:
        mock_validate.return_value = {"exchange_active": True, "trading_active": True}

        result = await market_ops.is_market_open()

        assert result is True


@pytest.mark.asyncio
async def test_is_market_open_exchange_inactive(market_ops, mock_client):
    with patch("common.kalshi_api.client_helpers.market_status_operations.validate_exchange_status_response") as mock_validate:
        mock_validate.return_value = {"exchange_active": False, "trading_active": True}

        result = await market_ops.is_market_open()

        assert result is False


@pytest.mark.asyncio
async def test_is_market_open_trading_inactive(market_ops, mock_client):
    with patch("common.kalshi_api.client_helpers.market_status_operations.validate_exchange_status_response") as mock_validate:
        mock_validate.return_value = {"exchange_active": True, "trading_active": False}

        result = await market_ops.is_market_open()

        assert result is False
