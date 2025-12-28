"""Tests for portfolio service module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.data_models.trading import PortfolioBalance, PortfolioPosition
from common.kalshi_trading_client.services.portfolio import PortfolioService
from common.trading_exceptions import KalshiAPIError


class TestPortfolioService:
    """Tests for PortfolioService class."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_portfolio_balance = AsyncMock()
        client.get_portfolio_positions = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_client):
        return PortfolioService(kalshi_client=mock_client)

    @pytest.mark.asyncio
    async def test_get_balance_success(self, service, mock_client):
        mock_balance = MagicMock(spec=PortfolioBalance)
        mock_balance.balance_cents = 10000
        mock_client.get_portfolio_balance.return_value = mock_balance

        result = await service.get_balance()

        assert result is mock_balance
        mock_client.get_portfolio_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_balance_api_error(self, service, mock_client):
        mock_client.get_portfolio_balance.side_effect = RuntimeError("API error")

        with pytest.raises(KalshiAPIError, match="Failed to retrieve portfolio balance"):
            await service.get_balance()

    @pytest.mark.asyncio
    async def test_get_positions_success(self, service, mock_client):
        mock_positions = [
            MagicMock(spec=PortfolioPosition),
            MagicMock(spec=PortfolioPosition),
        ]
        mock_client.get_portfolio_positions.return_value = mock_positions

        result = await service.get_positions()

        assert len(result) == 2
        mock_client.get_portfolio_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, service, mock_client):
        mock_client.get_portfolio_positions.return_value = []

        result = await service.get_positions()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_positions_api_error(self, service, mock_client):
        mock_client.get_portfolio_positions.side_effect = RuntimeError("API error")

        with pytest.raises(KalshiAPIError, match="Failed to retrieve portfolio positions"):
            await service.get_positions()
