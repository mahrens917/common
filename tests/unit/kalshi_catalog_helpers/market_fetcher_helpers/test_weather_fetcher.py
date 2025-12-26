"""Tests for weather_fetcher module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_api import KalshiClientError
from common.kalshi_catalog_helpers.market_fetcher import KalshiMarketCatalogError
from common.kalshi_catalog_helpers.market_fetcher_helpers.weather_fetcher import (
    WeatherFetcher,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock API client."""
    client = MagicMock()
    client.get_series = AsyncMock()
    return client


@pytest.fixture
def mock_fetcher_client() -> MagicMock:
    """Create a mock fetcher client."""
    client = MagicMock()
    client.fetch_markets = AsyncMock(return_value=1)
    return client


class TestWeatherFetcher:
    """Tests for WeatherFetcher class."""

    def test_init(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test WeatherFetcher initialization."""
        fetcher = WeatherFetcher(mock_client, mock_fetcher_client)
        assert fetcher._client is mock_client
        assert fetcher._fetcher_client is mock_fetcher_client

    @pytest.mark.asyncio
    async def test_fetch_weather_markets_success(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test successful weather market fetching."""
        mock_client.get_series.return_value = [
            {"ticker": "KXHIGHNY"},
            {"ticker": "KXHIGHCHI"},
        ]
        fetcher = WeatherFetcher(mock_client, mock_fetcher_client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_weather_markets("Climate", markets, seen_tickers)

        assert pages == 2
        assert mock_fetcher_client.fetch_markets.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_weather_markets_filters_non_kxhigh(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test that non-KXHIGH series are filtered out."""
        mock_client.get_series.return_value = [
            {"ticker": "KXHIGHNY"},
            {"ticker": "OTHERSERIES"},
            {"ticker": "KXLOWCHI"},
        ]
        fetcher = WeatherFetcher(mock_client, mock_fetcher_client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_weather_markets("Climate", markets, seen_tickers)

        assert pages == 1
        mock_fetcher_client.fetch_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_weather_markets_no_matching_series(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test raises error when no matching series found."""
        mock_client.get_series.return_value = [
            {"ticker": "OTHERSERIES"},
        ]
        fetcher = WeatherFetcher(mock_client, mock_fetcher_client)

        with pytest.raises(KalshiMarketCatalogError, match="no KXHIGH"):
            await fetcher.fetch_weather_markets("Climate", [], set())

    @pytest.mark.asyncio
    async def test_fetch_weather_markets_client_error(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test raises error on client error."""
        mock_client.get_series.side_effect = KalshiClientError("API error")
        fetcher = WeatherFetcher(mock_client, mock_fetcher_client)

        with pytest.raises(KalshiMarketCatalogError, match="Failed to fetch"):
            await fetcher.fetch_weather_markets("Climate", [], set())

    @pytest.mark.asyncio
    async def test_fetch_weather_markets_skips_invalid_series(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test that series without valid ticker are skipped."""
        mock_client.get_series.return_value = [
            {"ticker": "KXHIGHNY"},
            {"no_ticker": "value"},
            "not_a_dict",
            {"ticker": None},
        ]
        fetcher = WeatherFetcher(mock_client, mock_fetcher_client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_weather_markets("Climate", markets, seen_tickers)

        assert pages == 1

    @pytest.mark.asyncio
    async def test_fetch_weather_markets_passes_correct_params(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test that correct params are passed to fetcher."""
        mock_client.get_series.return_value = [{"ticker": "KXHIGHNY"}]
        fetcher = WeatherFetcher(mock_client, mock_fetcher_client)

        await fetcher.fetch_weather_markets("Climate", [], set())

        call_args = mock_fetcher_client.fetch_markets.call_args
        assert call_args[0][0] == "series KXHIGHNY"
        assert call_args[1]["base_params"]["category"] == "Climate"
        assert call_args[1]["base_params"]["series_ticker"] == "KXHIGHNY"
