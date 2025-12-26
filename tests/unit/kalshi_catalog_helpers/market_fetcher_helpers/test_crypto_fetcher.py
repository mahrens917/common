"""Tests for crypto_fetcher module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_api import KalshiClientError
from common.kalshi_catalog_helpers.market_fetcher import KalshiMarketCatalogError
from common.kalshi_catalog_helpers.market_fetcher_helpers.crypto_fetcher import (
    CryptoFetcher,
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


class TestCryptoFetcher:
    """Tests for CryptoFetcher class."""

    def test_init(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test CryptoFetcher initialization."""
        fetcher = CryptoFetcher(mock_client, ("BTC", "ETH"), mock_fetcher_client)
        assert fetcher._client is mock_client
        assert fetcher._crypto_assets == ("BTC", "ETH")
        assert fetcher._fetcher_client is mock_fetcher_client

    @pytest.mark.asyncio
    async def test_fetch_crypto_markets_success(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test successful crypto market fetching."""
        mock_client.get_series.return_value = [
            {"ticker": "KXBTC"},
            {"ticker": "KXETH"},
        ]
        fetcher = CryptoFetcher(mock_client, ("BTC", "ETH"), mock_fetcher_client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_crypto_markets(markets, seen_tickers)

        assert pages == 2
        assert mock_fetcher_client.fetch_markets.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_crypto_markets_filters_non_crypto(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test that non-crypto series are filtered out."""
        mock_client.get_series.return_value = [
            {"ticker": "KXBTC"},
            {"ticker": "WEATHER"},
            {"ticker": "POLITICS"},
        ]
        fetcher = CryptoFetcher(mock_client, ("BTC", "ETH"), mock_fetcher_client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_crypto_markets(markets, seen_tickers)

        assert pages == 1
        mock_fetcher_client.fetch_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_crypto_markets_no_matching_series(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test raises error when no matching series found."""
        mock_client.get_series.return_value = [
            {"ticker": "WEATHER"},
            {"ticker": "POLITICS"},
        ]
        fetcher = CryptoFetcher(mock_client, ("BTC", "ETH"), mock_fetcher_client)
        markets: list = []
        seen_tickers: set = set()

        with pytest.raises(KalshiMarketCatalogError, match="no BTC/ETH"):
            await fetcher.fetch_crypto_markets(markets, seen_tickers)

    @pytest.mark.asyncio
    async def test_fetch_crypto_markets_client_error(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test raises error on client error."""
        mock_client.get_series.side_effect = KalshiClientError("API error")
        fetcher = CryptoFetcher(mock_client, ("BTC", "ETH"), mock_fetcher_client)

        with pytest.raises(KalshiMarketCatalogError, match="Failed to fetch"):
            await fetcher.fetch_crypto_markets([], set())

    @pytest.mark.asyncio
    async def test_fetch_crypto_markets_skips_invalid_series(self, mock_client: MagicMock, mock_fetcher_client: MagicMock) -> None:
        """Test that series without ticker are skipped."""
        mock_client.get_series.return_value = [
            {"ticker": "KXBTC"},
            {"no_ticker": "value"},
            "not_a_dict",
        ]
        fetcher = CryptoFetcher(mock_client, ("BTC", "ETH"), mock_fetcher_client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_crypto_markets(markets, seen_tickers)

        assert pages == 1
