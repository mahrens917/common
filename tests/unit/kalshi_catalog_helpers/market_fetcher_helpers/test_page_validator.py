"""Tests for page_validator module."""

import pytest

from common.kalshi_catalog_helpers.market_fetcher import KalshiMarketCatalogError
from common.kalshi_catalog_helpers.market_fetcher_helpers.page_validator import PageValidator


class TestPageValidator:
    """Tests for PageValidator class."""

    def test_extract_markets_with_valid_list(self) -> None:
        """Test extracting markets from valid payload."""
        payload = {"markets": [{"id": 1}, {"id": 2}]}
        result = PageValidator.extract_markets(payload)
        assert result == [{"id": 1}, {"id": 2}]

    def test_extract_markets_with_empty_list(self) -> None:
        """Test extracting markets from payload with empty list."""
        payload = {"markets": []}
        result = PageValidator.extract_markets(payload)
        assert result == []

    def test_extract_markets_missing_markets_key(self) -> None:
        """Test extraction raises error when markets key is missing."""
        payload = {"other_key": "value"}
        with pytest.raises(KalshiMarketCatalogError, match="missing 'markets'"):
            PageValidator.extract_markets(payload)

    def test_extract_markets_with_non_list_value(self) -> None:
        """Test extraction raises error when markets is not a list."""
        payload = {"markets": "not_a_list"}
        with pytest.raises(KalshiMarketCatalogError, match="missing 'markets'"):
            PageValidator.extract_markets(payload)

    def test_extract_markets_with_none_value(self) -> None:
        """Test extraction raises error when markets is None."""
        payload = {"markets": None}
        with pytest.raises(KalshiMarketCatalogError, match="missing 'markets'"):
            PageValidator.extract_markets(payload)
