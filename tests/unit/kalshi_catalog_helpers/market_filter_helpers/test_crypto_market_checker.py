"""Tests for kalshi_catalog_helpers.market_filter_helpers.crypto_market_checker module."""

import pytest

from common.kalshi_catalog_helpers.market_filter_helpers.crypto_market_checker import (
    is_crypto_market,
)


class TestIsCryptoMarket:
    """Tests for is_crypto_market function."""

    def test_crypto_ticker(self) -> None:
        """Test market with crypto ticker."""
        market = {"ticker": "KXBTC-25JAN01-100000"}

        assert is_crypto_market(market) is True

    def test_eth_ticker(self) -> None:
        """Test market with ETH ticker."""
        market = {"ticker": "KXETH-25JAN01-5000"}

        assert is_crypto_market(market) is True

    def test_weather_ticker(self) -> None:
        """Test market with weather ticker."""
        market = {"ticker": "KXMIA-25JAN01-75"}

        assert is_crypto_market(market) is False

    def test_crypto_currency_field(self) -> None:
        """Test market with crypto currency field."""
        market = {"ticker": "SOMEMARKET", "currency": "BTC"}

        assert is_crypto_market(market) is True

    def test_crypto_underlying_field(self) -> None:
        """Test market with crypto underlying field."""
        market = {"ticker": "SOMEMARKET", "underlying": "ETH"}

        assert is_crypto_market(market) is True

    def test_crypto_underlying_symbol_field(self) -> None:
        """Test market with crypto underlying_symbol field."""
        market = {"ticker": "SOMEMARKET", "underlying_symbol": "BTCUSD"}

        assert is_crypto_market(market) is True

    def test_crypto_underlying_asset_field(self) -> None:
        """Test market with crypto underlying_asset field."""
        market = {"ticker": "SOMEMARKET", "underlying_asset": "BTC"}

        assert is_crypto_market(market) is True

    def test_crypto_asset_field(self) -> None:
        """Test market with crypto asset field."""
        market = {"ticker": "SOMEMARKET", "asset": "ETH"}

        assert is_crypto_market(market) is True

    def test_crypto_series_ticker_field(self) -> None:
        """Test market with crypto series_ticker field."""
        market = {"ticker": "SOMEMARKET", "series_ticker": "KXBTC"}

        assert is_crypto_market(market) is True

    def test_crypto_product_ticker_field(self) -> None:
        """Test market with crypto product_ticker field."""
        market = {"ticker": "SOMEMARKET", "product_ticker": "KXETH"}

        assert is_crypto_market(market) is True

    def test_non_crypto_market(self) -> None:
        """Test non-crypto market."""
        market = {
            "ticker": "WEATHER-25JAN01",
            "currency": "USD",
            "underlying": "TEMPERATURE",
        }

        assert is_crypto_market(market) is False

    def test_empty_market(self) -> None:
        """Test empty market dict."""
        market: dict[str, object] = {}

        assert is_crypto_market(market) is False

    def test_non_string_ticker(self) -> None:
        """Test market with non-string ticker."""
        market = {"ticker": 12345}

        assert is_crypto_market(market) is False

    def test_non_string_currency(self) -> None:
        """Test market with non-string currency field."""
        market = {"ticker": "SOMEMARKET", "currency": 123}

        assert is_crypto_market(market) is False
