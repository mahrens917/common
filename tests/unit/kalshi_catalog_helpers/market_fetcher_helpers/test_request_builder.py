"""Tests for request_builder module."""

from common.kalshi_catalog_helpers.market_fetcher_helpers.request_builder import RequestBuilder


class TestRequestBuilder:
    """Tests for RequestBuilder class."""

    def test_build_params_with_base_params_and_cursor(self) -> None:
        """Test building params with base params and cursor."""
        base_params = {"series_ticker": "KXBTC"}
        result = RequestBuilder.build_params(base_params, "abc123", "open")
        assert result == {"series_ticker": "KXBTC", "status": "open", "cursor": "abc123"}

    def test_build_params_with_base_params_no_cursor(self) -> None:
        """Test building params with base params but no cursor."""
        base_params = {"series_ticker": "KXBTC"}
        result = RequestBuilder.build_params(base_params, None, "open")
        assert result == {"series_ticker": "KXBTC", "status": "open"}

    def test_build_params_without_base_params(self) -> None:
        """Test building params without base params."""
        result = RequestBuilder.build_params(None, None, "closed")
        assert result == {"status": "closed"}

    def test_build_params_without_base_params_with_cursor(self) -> None:
        """Test building params without base params but with cursor."""
        result = RequestBuilder.build_params(None, "cursor123", "active")
        assert result == {"status": "active", "cursor": "cursor123"}

    def test_build_params_does_not_modify_original(self) -> None:
        """Test that original base_params is not modified."""
        base_params = {"key": "value"}
        RequestBuilder.build_params(base_params, "cursor", "open")
        assert base_params == {"key": "value"}

    def test_build_params_with_empty_base_params(self) -> None:
        """Test building params with empty base params dict."""
        result = RequestBuilder.build_params({}, "cursor", "open")
        assert result == {"status": "open", "cursor": "cursor"}
