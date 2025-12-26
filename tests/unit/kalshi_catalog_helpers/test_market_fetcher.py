"""Tests for market_fetcher module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.kalshi_catalog_helpers.market_fetcher import (
    KalshiMarketCatalogError,
    MarketFetcher,
    MarketFetcherClient,
    _add_markets,
    _build_request_params,
    _extract_next_cursor,
    _extract_page_markets,
    _fetch_page,
    _should_continue_pagination,
)


class TestBuildRequestParams:
    """Tests for _build_request_params function."""

    def test_with_base_params(self) -> None:
        """Test building params with base params."""
        client = MagicMock()
        client._market_status = "open"
        base_params = {"category": "Crypto"}

        result = _build_request_params(client, base_params, None)

        assert result["category"] == "Crypto"
        assert result["status"] == "open"
        assert "cursor" not in result

    def test_with_cursor(self) -> None:
        """Test building params with cursor."""
        client = MagicMock()
        client._market_status = "open"

        result = _build_request_params(client, None, "abc123")

        assert result["status"] == "open"
        assert result["cursor"] == "abc123"

    def test_without_base_params(self) -> None:
        """Test building params without base params."""
        client = MagicMock()
        client._market_status = "active"

        result = _build_request_params(client, None, None)

        assert result == {"status": "active"}


class TestFetchPage:
    """Tests for _fetch_page function."""

    @pytest.mark.asyncio
    async def test_fetch_page_success(self) -> None:
        """Test successful page fetch."""
        client = MagicMock()
        client.api_request = AsyncMock(return_value={"markets": []})

        result = await _fetch_page(client, {"status": "open"})

        assert result == {"markets": []}
        client.api_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_page_client_error(self) -> None:
        """Test fetch page raises on client error."""
        from common.kalshi_api import KalshiClientError

        client = MagicMock()
        client.api_request = AsyncMock(side_effect=KalshiClientError("API error"))

        with pytest.raises(KalshiMarketCatalogError, match="request failed"):
            await _fetch_page(client, {"status": "open"})

    @pytest.mark.asyncio
    async def test_fetch_page_non_dict_response(self) -> None:
        """Test fetch page raises on non-dict response."""
        client = MagicMock()
        client.api_request = AsyncMock(return_value="not a dict")

        with pytest.raises(KalshiMarketCatalogError, match="not a JSON object"):
            await _fetch_page(client, {"status": "open"})


class TestExtractPageMarkets:
    """Tests for _extract_page_markets function."""

    def test_extract_markets_list(self) -> None:
        """Test extracting markets list."""
        payload = {"markets": [{"ticker": "ABC"}]}

        result = _extract_page_markets(payload)

        assert result == [{"ticker": "ABC"}]

    def test_extract_markets_missing(self) -> None:
        """Test raises when markets key missing."""
        with pytest.raises(KalshiMarketCatalogError, match="missing 'markets'"):
            _extract_page_markets({})

    def test_extract_markets_not_list(self) -> None:
        """Test raises when markets is not a list."""
        with pytest.raises(KalshiMarketCatalogError, match="missing 'markets'"):
            _extract_page_markets({"markets": "not a list"})


class TestShouldContinuePagination:
    """Tests for _should_continue_pagination function."""

    def test_new_cursor(self) -> None:
        """Test returns True for new cursor."""
        assert _should_continue_pagination("abc", set(), "test") is True

    def test_repeated_cursor(self) -> None:
        """Test returns False for repeated cursor."""
        assert _should_continue_pagination("abc", {"abc"}, "test") is False

    def test_none_cursor_not_seen(self) -> None:
        """Test None cursor not in seen set returns True."""
        assert _should_continue_pagination(None, set(), "test") is True


class TestExtractNextCursor:
    """Tests for _extract_next_cursor function."""

    def test_valid_cursor(self) -> None:
        """Test extracting valid cursor."""
        assert _extract_next_cursor({"cursor": "abc123"}) == "abc123"

    def test_none_cursor(self) -> None:
        """Test None cursor returns None."""
        assert _extract_next_cursor({"cursor": None}) is None

    def test_missing_cursor(self) -> None:
        """Test missing cursor returns None."""
        assert _extract_next_cursor({}) is None

    def test_empty_cursor(self) -> None:
        """Test empty string cursor returns None."""
        assert _extract_next_cursor({"cursor": ""}) is None

    def test_whitespace_cursor(self) -> None:
        """Test whitespace cursor returns None."""
        assert _extract_next_cursor({"cursor": "   "}) is None

    def test_non_string_cursor(self) -> None:
        """Test non-string cursor returns None."""
        assert _extract_next_cursor({"cursor": 123}) is None


class TestAddMarkets:
    """Tests for _add_markets function."""

    def test_add_valid_markets(self) -> None:
        """Test adding valid markets."""
        page_markets = [{"ticker": "ABC"}, {"ticker": "DEF"}]
        markets: list = []
        seen_tickers: set = set()

        added = _add_markets(page_markets, markets, seen_tickers, "test", None)

        assert added == 2
        assert len(markets) == 2
        assert "ABC" in seen_tickers
        assert "DEF" in seen_tickers

    def test_skip_duplicate_tickers(self) -> None:
        """Test skipping duplicate tickers."""
        page_markets = [{"ticker": "ABC"}, {"ticker": "abc"}]
        markets: list = []
        seen_tickers: set = set()

        added = _add_markets(page_markets, markets, seen_tickers, "test", None)

        assert added == 1
        assert len(markets) == 1

    def test_uppercase_tickers(self) -> None:
        """Test tickers are uppercased."""
        page_markets = [{"ticker": "abc"}]
        markets: list = []
        seen_tickers: set = set()

        _add_markets(page_markets, markets, seen_tickers, "test", None)

        assert markets[0]["ticker"] == "ABC"

    def test_missing_ticker_raises(self) -> None:
        """Test raises on missing ticker."""
        page_markets = [{"no_ticker": "value"}]

        with pytest.raises(KalshiMarketCatalogError, match="missing ticker"):
            _add_markets(page_markets, [], set(), "test", None)

    def test_empty_ticker_raises(self) -> None:
        """Test raises on empty ticker."""
        page_markets = [{"ticker": ""}]

        with pytest.raises(KalshiMarketCatalogError, match="missing ticker"):
            _add_markets(page_markets, [], set(), "test", None)

    def test_adds_category_from_base_params(self) -> None:
        """Test adds category from base params."""
        page_markets = [{"ticker": "ABC"}]
        markets: list = []
        base_params = {"category": "Crypto"}

        _add_markets(page_markets, markets, set(), "test", base_params)

        assert markets[0]["__category"] == "Crypto"

    def test_uses_label_when_no_category(self) -> None:
        """Test uses label when no category in params."""
        page_markets = [{"ticker": "ABC"}]
        markets: list = []

        _add_markets(page_markets, markets, set(), "Weather", None)

        assert markets[0]["__category"] == "Weather"


class TestMarketFetcherClient:
    """Tests for MarketFetcherClient class."""

    def test_init(self) -> None:
        """Test MarketFetcherClient initialization."""
        client = MagicMock()
        fetcher = MarketFetcherClient(client)
        assert fetcher._client is client

    @pytest.mark.asyncio
    async def test_fetch_markets_single_page(self) -> None:
        """Test fetching markets from single page."""
        client = MagicMock()
        client._market_status = "open"
        client.api_request = AsyncMock(return_value={"markets": [{"ticker": "ABC"}], "cursor": None})
        fetcher = MarketFetcherClient(client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_markets("test", markets, seen_tickers, None)

        assert pages == 0
        assert len(markets) == 1

    @pytest.mark.asyncio
    async def test_fetch_markets_multiple_pages(self) -> None:
        """Test fetching markets from multiple pages."""
        client = MagicMock()
        client._market_status = "open"
        client.api_request = AsyncMock(
            side_effect=[
                {"markets": [{"ticker": "ABC"}], "cursor": "page2"},
                {"markets": [{"ticker": "DEF"}], "cursor": None},
            ]
        )
        fetcher = MarketFetcherClient(client)
        markets: list = []
        seen_tickers: set = set()

        pages = await fetcher.fetch_markets("test", markets, seen_tickers, None)

        assert pages == 1
        assert len(markets) == 2


class TestMarketFetcher:
    """Tests for MarketFetcher class."""

    def test_init(self) -> None:
        """Test MarketFetcher initialization."""
        client = MagicMock()
        fetcher = MarketFetcher(client, "open", ("BTC", "ETH"))

        assert fetcher._client is client
        assert fetcher._crypto_assets == ("BTC", "ETH")
        assert client._market_status == "open"

    @pytest.mark.asyncio
    async def test_fetch_all_markets_no_categories(self) -> None:
        """Test fetch all markets without categories."""
        client = MagicMock()
        client._market_status = "open"
        client.api_request = AsyncMock(return_value={"markets": [{"ticker": "ABC"}], "cursor": None})
        fetcher = MarketFetcher(client, "open", ("BTC",))

        markets, pages = await fetcher.fetch_all_markets(None)

        assert len(markets) == 1

    @pytest.mark.asyncio
    async def test_fetch_all_markets_with_crypto(self) -> None:
        """Test fetch all markets with Crypto category."""
        client = MagicMock()
        client._market_status = "open"
        client.get_series = AsyncMock(return_value=[{"ticker": "KXBTC"}])
        client.api_request = AsyncMock(return_value={"markets": [{"ticker": "KXBTC-T100"}], "cursor": None})
        fetcher = MarketFetcher(client, "open", ("BTC",))

        markets, pages = await fetcher.fetch_all_markets(["Crypto"])

        assert len(markets) == 1

    @pytest.mark.asyncio
    async def test_fetch_all_markets_with_weather(self) -> None:
        """Test fetch all markets with Weather category."""
        client = MagicMock()
        client._market_status = "open"
        client.get_series = AsyncMock(return_value=[{"ticker": "KXHIGHNY"}])
        client.api_request = AsyncMock(return_value={"markets": [{"ticker": "KXHIGH-T100"}], "cursor": None})
        fetcher = MarketFetcher(client, "open", ("BTC",))

        markets, pages = await fetcher.fetch_all_markets(["Weather"])

        assert len(markets) == 1

    @pytest.mark.asyncio
    async def test_fetch_crypto_no_matching_series(self) -> None:
        """Test crypto fetch raises when no matching series."""
        client = MagicMock()
        client._market_status = "open"
        client.get_series = AsyncMock(return_value=[{"ticker": "OTHER"}])
        fetcher = MarketFetcher(client, "open", ("BTC", "ETH"))

        with pytest.raises(KalshiMarketCatalogError, match="no BTC/ETH"):
            await fetcher.fetch_all_markets(["Crypto"])

    @pytest.mark.asyncio
    async def test_fetch_weather_no_matching_series(self) -> None:
        """Test weather fetch raises when no matching series."""
        client = MagicMock()
        client._market_status = "open"
        client.get_series = AsyncMock(return_value=[{"ticker": "OTHER"}])
        fetcher = MarketFetcher(client, "open", ("BTC",))

        with pytest.raises(KalshiMarketCatalogError, match="no KXHIGH"):
            await fetcher.fetch_all_markets(["Weather"])

    @pytest.mark.asyncio
    async def test_fetch_crypto_client_error(self) -> None:
        """Test crypto fetch raises on client error."""
        from common.kalshi_api import KalshiClientError

        client = MagicMock()
        client._market_status = "open"
        client.get_series = AsyncMock(side_effect=KalshiClientError("error"))
        fetcher = MarketFetcher(client, "open", ("BTC",))

        with pytest.raises(KalshiMarketCatalogError, match="Failed to fetch"):
            await fetcher.fetch_all_markets(["Crypto"])

    @pytest.mark.asyncio
    async def test_fetch_weather_client_error(self) -> None:
        """Test weather fetch raises on client error."""
        from common.kalshi_api import KalshiClientError

        client = MagicMock()
        client._market_status = "open"
        client.get_series = AsyncMock(side_effect=KalshiClientError("error"))
        fetcher = MarketFetcher(client, "open", ("BTC",))

        with pytest.raises(KalshiMarketCatalogError, match="Failed to fetch"):
            await fetcher.fetch_all_markets(["Climate and Weather"])
