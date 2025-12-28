"""Tests for fills_fetcher module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_trading_client.services.order_helpers.fills_fetcher import FillsFetcher
from common.trading_exceptions import KalshiAPIError


class TestFillsFetcher:
    """Tests for FillsFetcher class."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_fills = AsyncMock()
        client.get_all_fills = AsyncMock()
        return client

    @pytest.fixture
    def fetcher(self, mock_client):
        return FillsFetcher(mock_client)

    @pytest.mark.asyncio
    async def test_get_fills_success(self, fetcher, mock_client):
        mock_client.get_fills.return_value = [
            {"fill_id": "fill-1", "price": 50, "count": 10},
            {"fill_id": "fill-2", "price": 55, "count": 5},
        ]

        result = await fetcher.get_fills("order-123")

        assert len(result) == 2
        assert result[0]["fill_id"] == "fill-1"
        mock_client.get_fills.assert_called_once_with("order-123")

    @pytest.mark.asyncio
    async def test_get_fills_api_error(self, fetcher, mock_client):
        mock_client.get_fills.side_effect = RuntimeError("API error")

        with pytest.raises(KalshiAPIError, match="Failed to get fills"):
            await fetcher.get_fills("order-123")

    @pytest.mark.asyncio
    async def test_get_all_fills_success(self, fetcher, mock_client):
        mock_client.get_all_fills.return_value = {
            "fills": [{"fill_id": "fill-1"}],
            "cursor": "next-cursor",
        }

        result = await fetcher.get_all_fills(
            min_ts=1000000,
            max_ts=2000000,
            ticker="TICKER-ABC",
            cursor=None,
        )

        assert "fills" in result
        assert result["cursor"] == "next-cursor"
        mock_client.get_all_fills.assert_called_once_with(1000000, 2000000, "TICKER-ABC", None)

    @pytest.mark.asyncio
    async def test_get_all_fills_with_cursor(self, fetcher, mock_client):
        mock_client.get_all_fills.return_value = {"fills": [], "cursor": None}

        result = await fetcher.get_all_fills(
            min_ts=None,
            max_ts=None,
            ticker=None,
            cursor="prev-cursor",
        )

        assert result["fills"] == []
        mock_client.get_all_fills.assert_called_once_with(None, None, None, "prev-cursor")

    @pytest.mark.asyncio
    async def test_get_all_fills_api_error(self, fetcher, mock_client):
        mock_client.get_all_fills.side_effect = RuntimeError("API error")

        with pytest.raises(KalshiAPIError, match="Failed to get all fills"):
            await fetcher.get_all_fills(None, None, None, None)
