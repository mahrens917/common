"""Tests for kalshi_catalog_helpers.market_filter_helpers.crypto_pattern_matcher module."""

import pytest

from common.kalshi_catalog_helpers.market_filter_helpers.crypto_pattern_matcher import (
    matches_crypto_prefix,
    token_matches_asset,
    token_matches_crypto,
    value_matches_crypto,
)


class TestMatchesCryptoPrefix:
    """Tests for matches_crypto_prefix function."""

    def test_btc_prefix(self) -> None:
        """Test BTC prefix matches."""
        assert matches_crypto_prefix("BTC-25JAN01") is True

    def test_eth_prefix(self) -> None:
        """Test ETH prefix matches."""
        assert matches_crypto_prefix("ETH-25JAN01") is True

    def test_kxbtc_prefix(self) -> None:
        """Test KXBTC prefix matches."""
        assert matches_crypto_prefix("KXBTC-25JAN01-100000") is True

    def test_kxeth_prefix(self) -> None:
        """Test KXETH prefix matches."""
        assert matches_crypto_prefix("KXETH-25JAN01-5000") is True

    def test_non_crypto_prefix(self) -> None:
        """Test non-crypto prefix does not match."""
        assert matches_crypto_prefix("KXMIA-25JAN01") is False

    def test_weather_prefix(self) -> None:
        """Test weather market does not match."""
        assert matches_crypto_prefix("HIGHTEMP-25JAN01") is False


class TestTokenMatchesAsset:
    """Tests for token_matches_asset function."""

    def test_exact_match(self) -> None:
        """Test exact asset match."""
        assert token_matches_asset("BTC", "BTC") is True
        assert token_matches_asset("ETH", "ETH") is True

    def test_asset_with_digits(self) -> None:
        """Test asset with trailing digits."""
        assert token_matches_asset("BTC25", "BTC") is True
        assert token_matches_asset("ETH01", "ETH") is True

    def test_asset_with_max_suffix(self) -> None:
        """Test asset with MAX suffix."""
        assert token_matches_asset("BTCMAX", "BTC") is True

    def test_asset_with_min_suffix(self) -> None:
        """Test asset with MIN suffix."""
        assert token_matches_asset("ETHMIN", "ETH") is True

    def test_asset_with_t_suffix(self) -> None:
        """Test asset with T suffix."""
        assert token_matches_asset("BTCT", "BTC") is True

    def test_asset_with_b_suffix(self) -> None:
        """Test asset with B suffix."""
        assert token_matches_asset("ETHB", "ETH") is True

    def test_asset_with_usd_suffix(self) -> None:
        """Test asset with USD suffix."""
        assert token_matches_asset("BTCUSD", "BTC") is True

    def test_non_matching_asset(self) -> None:
        """Test non-matching asset."""
        assert token_matches_asset("SOL", "BTC") is False

    def test_asset_with_other_suffix(self) -> None:
        """Test asset with unrecognized suffix."""
        assert token_matches_asset("BTCXYZ", "BTC") is False


class TestTokenMatchesCrypto:
    """Tests for token_matches_crypto function."""

    def test_kxbtc_token(self) -> None:
        """Test KXBTC token matches."""
        assert token_matches_crypto("KXBTC") is True

    def test_kxeth_token(self) -> None:
        """Test KXETH token matches."""
        assert token_matches_crypto("KXETH") is True

    def test_btc_token(self) -> None:
        """Test BTC token matches."""
        assert token_matches_crypto("BTC") is True

    def test_eth_token(self) -> None:
        """Test ETH token matches."""
        assert token_matches_crypto("ETH") is True

    def test_btc_with_suffix(self) -> None:
        """Test BTC with suffix matches."""
        assert token_matches_crypto("BTCMAX") is True

    def test_non_crypto_token(self) -> None:
        """Test non-crypto token does not match."""
        assert token_matches_crypto("MIA") is False
        assert token_matches_crypto("WEATHER") is False


class TestValueMatchesCrypto:
    """Tests for value_matches_crypto function."""

    def test_btc_ticker(self) -> None:
        """Test BTC ticker matches."""
        assert value_matches_crypto("BTC-25JAN01-100000") is True

    def test_eth_ticker(self) -> None:
        """Test ETH ticker matches."""
        assert value_matches_crypto("ETH-25JAN01-5000") is True

    def test_kxbtc_ticker(self) -> None:
        """Test KXBTC ticker matches."""
        assert value_matches_crypto("KXBTC-25JAN01-T100000") is True

    def test_lowercase_crypto(self) -> None:
        """Test lowercase crypto matches."""
        assert value_matches_crypto("btc-25jan01") is True

    def test_weather_ticker(self) -> None:
        """Test weather ticker does not match."""
        assert value_matches_crypto("KXMIA-25JAN01-75") is False

    def test_mixed_content(self) -> None:
        """Test mixed content with crypto token."""
        assert value_matches_crypto("SOME-BTC-THING") is True

    def test_no_crypto_content(self) -> None:
        """Test content without crypto."""
        assert value_matches_crypto("WEATHER-MIAMI-TEMP") is False

    def test_empty_string(self) -> None:
        """Test empty string."""
        assert value_matches_crypto("") is False
