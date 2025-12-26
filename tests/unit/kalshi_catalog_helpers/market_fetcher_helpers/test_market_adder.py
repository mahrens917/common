"""Tests for market_adder module."""

import pytest

from common.kalshi_catalog_helpers.market_fetcher import KalshiMarketCatalogError
from common.kalshi_catalog_helpers.market_fetcher_helpers.market_adder import MarketAdder


class TestMarketAdder:
    """Tests for MarketAdder class."""

    def test_add_markets_single_market(self) -> None:
        """Test adding a single market."""
        page_markets = [{"ticker": "KXBTC-24DEC25", "price": 100}]
        markets: list = []
        seen_tickers: set = set()

        added = MarketAdder.add_markets(page_markets, markets, seen_tickers, "test_label", None)

        assert added == 1
        assert len(markets) == 1
        assert markets[0]["ticker"] == "KXBTC-24DEC25"
        assert "KXBTC-24DEC25" in seen_tickers

    def test_add_markets_deduplicates(self) -> None:
        """Test that duplicate tickers are skipped."""
        page_markets = [{"ticker": "KXBTC-24DEC25"}]
        markets: list = []
        seen_tickers: set = {"KXBTC-24DEC25"}

        added = MarketAdder.add_markets(page_markets, markets, seen_tickers, "test", None)

        assert added == 0
        assert len(markets) == 0

    def test_add_markets_normalizes_ticker_case(self) -> None:
        """Test that tickers are normalized to uppercase."""
        page_markets = [{"ticker": "kxbtc-24dec25"}]
        markets: list = []
        seen_tickers: set = set()

        added = MarketAdder.add_markets(page_markets, markets, seen_tickers, "test", None)

        assert added == 1
        assert markets[0]["ticker"] == "KXBTC-24DEC25"
        assert "KXBTC-24DEC25" in seen_tickers

    def test_add_markets_missing_ticker_raises_error(self) -> None:
        """Test that missing ticker raises error."""
        page_markets = [{"price": 100}]
        markets: list = []
        seen_tickers: set = set()

        with pytest.raises(KalshiMarketCatalogError, match="missing ticker"):
            MarketAdder.add_markets(page_markets, markets, seen_tickers, "test", None)

    def test_add_markets_empty_ticker_raises_error(self) -> None:
        """Test that empty ticker raises error."""
        page_markets = [{"ticker": "   "}]
        markets: list = []
        seen_tickers: set = set()

        with pytest.raises(KalshiMarketCatalogError, match="missing ticker"):
            MarketAdder.add_markets(page_markets, markets, seen_tickers, "test", None)

    def test_add_markets_non_dict_market_raises_error(self) -> None:
        """Test that non-dict market raises error."""
        page_markets = ["not_a_dict"]
        markets: list = []
        seen_tickers: set = set()

        with pytest.raises(KalshiMarketCatalogError, match="missing ticker"):
            MarketAdder.add_markets(page_markets, markets, seen_tickers, "test", None)

    def test_add_markets_sets_category_from_params(self) -> None:
        """Test that category is set from base_params."""
        page_markets = [{"ticker": "KXBTC-24DEC25"}]
        markets: list = []
        seen_tickers: set = set()
        base_params = {"category": "Crypto"}

        MarketAdder.add_markets(page_markets, markets, seen_tickers, "test_label", base_params)

        assert markets[0]["__category"] == "Crypto"

    def test_add_markets_sets_category_from_label(self) -> None:
        """Test that category falls back to label."""
        page_markets = [{"ticker": "KXBTC-24DEC25"}]
        markets: list = []
        seen_tickers: set = set()

        MarketAdder.add_markets(page_markets, markets, seen_tickers, "test_label", None)

        assert markets[0]["__category"] == "test_label"

    def test_add_markets_multiple(self) -> None:
        """Test adding multiple markets."""
        page_markets = [
            {"ticker": "MARKET1"},
            {"ticker": "MARKET2"},
            {"ticker": "MARKET3"},
        ]
        markets: list = []
        seen_tickers: set = set()

        added = MarketAdder.add_markets(page_markets, markets, seen_tickers, "test", None)

        assert added == 3
        assert len(markets) == 3
