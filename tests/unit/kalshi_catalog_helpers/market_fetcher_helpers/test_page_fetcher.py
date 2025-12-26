"""Tests for page_fetcher module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_api import KalshiClientError
from common.kalshi_catalog_helpers.market_fetcher import KalshiMarketCatalogError
from common.kalshi_catalog_helpers.market_fetcher_helpers.page_fetcher import PageFetcher


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock API client."""
    client = MagicMock()
    client.api_request = AsyncMock()
    return client


class TestPageFetcher:
    """Tests for PageFetcher class."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test PageFetcher initialization."""
        fetcher = PageFetcher(mock_client)
        assert fetcher._client is mock_client

    @pytest.mark.asyncio
    async def test_fetch_page_success(self, mock_client: MagicMock) -> None:
        """Test fetching a page successfully."""
        expected_payload = {"markets": [{"id": 1}], "cursor": "next"}
        mock_client.api_request.return_value = expected_payload

        fetcher = PageFetcher(mock_client)
        result = await fetcher.fetch_page({"status": "open"})

        assert result == expected_payload
        mock_client.api_request.assert_called_once_with(
            method="GET",
            path="/trade-api/v2/markets",
            params={"status": "open"},
            operation_name="fetch_markets",
        )

    @pytest.mark.asyncio
    async def test_fetch_page_client_error(self, mock_client: MagicMock) -> None:
        """Test fetch_page raises KalshiMarketCatalogError on client error."""
        mock_client.api_request.side_effect = KalshiClientError("API error")

        fetcher = PageFetcher(mock_client)
        with pytest.raises(KalshiMarketCatalogError, match="request failed"):
            await fetcher.fetch_page({"status": "open"})

    @pytest.mark.asyncio
    async def test_fetch_page_non_dict_response(self, mock_client: MagicMock) -> None:
        """Test fetch_page raises error when response is not a dict."""
        mock_client.api_request.return_value = ["not", "a", "dict"]

        fetcher = PageFetcher(mock_client)
        with pytest.raises(KalshiMarketCatalogError, match="not a JSON object"):
            await fetcher.fetch_page({"status": "open"})

    @pytest.mark.asyncio
    async def test_fetch_page_string_response(self, mock_client: MagicMock) -> None:
        """Test fetch_page raises error when response is a string."""
        mock_client.api_request.return_value = "string_response"

        fetcher = PageFetcher(mock_client)
        with pytest.raises(KalshiMarketCatalogError, match="not a JSON object"):
            await fetcher.fetch_page({"status": "open"})
