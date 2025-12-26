"""Tests for kalshi_catalog_helpers.market_filter module."""

from unittest.mock import MagicMock, patch

import pytest

from common.kalshi_catalog_helpers.market_filter import (
    CRYPTO_ASSETS,
    CRYPTO_FIELD_CANDIDATES,
    CRYPTO_MONTH_PATTERN,
    CRYPTO_TICKER_PREFIXES,
    TOKEN_SPLIT_PATTERN,
    VALID_CRYPTO_STRIKE_TYPES,
    CryptoMarketValidator,
    MarketFilter,
    _close_time_in_future,
    _create_empty_stats,
    _extract_weather_station_token,
    _is_valid_market,
    _is_weather_market,
    _passes_weather_filters,
    _process_market_entry,
    _token_matches_asset,
    _token_matches_crypto,
    _value_matches_crypto,
)


class TestConstants:
    """Tests for module constants."""

    def test_crypto_assets(self) -> None:
        """Test CRYPTO_ASSETS tuple."""
        assert "BTC" in CRYPTO_ASSETS
        assert "ETH" in CRYPTO_ASSETS

    def test_crypto_ticker_prefixes(self) -> None:
        """Test CRYPTO_TICKER_PREFIXES tuple."""
        assert "KXBTC" in CRYPTO_TICKER_PREFIXES
        assert "KXETH" in CRYPTO_TICKER_PREFIXES

    def test_crypto_field_candidates(self) -> None:
        """Test CRYPTO_FIELD_CANDIDATES tuple."""
        assert "currency" in CRYPTO_FIELD_CANDIDATES
        assert "underlying" in CRYPTO_FIELD_CANDIDATES
        assert "asset" in CRYPTO_FIELD_CANDIDATES

    def test_valid_crypto_strike_types(self) -> None:
        """Test VALID_CRYPTO_STRIKE_TYPES tuple."""
        assert "greater" in VALID_CRYPTO_STRIKE_TYPES
        assert "less" in VALID_CRYPTO_STRIKE_TYPES
        assert "between" in VALID_CRYPTO_STRIKE_TYPES

    def test_token_split_pattern(self) -> None:
        """Test TOKEN_SPLIT_PATTERN regex."""
        result = TOKEN_SPLIT_PATTERN.split("KXBTC-25JAN01")
        assert "KXBTC" in result

    def test_crypto_month_pattern(self) -> None:
        """Test CRYPTO_MONTH_PATTERN regex."""
        assert CRYPTO_MONTH_PATTERN.search("25JAN01")
        assert CRYPTO_MONTH_PATTERN.search("KXBTC-25DEC31-T100000")
        assert not CRYPTO_MONTH_PATTERN.search("INVALID")


class TestHelperFunctions:
    """Tests for module helper functions."""

    def test_value_matches_crypto(self) -> None:
        """Test _value_matches_crypto function."""
        assert _value_matches_crypto("KXBTC") is True
        assert _value_matches_crypto("WEATHER") is False

    def test_token_matches_crypto(self) -> None:
        """Test _token_matches_crypto function."""
        assert _token_matches_crypto("BTC") is True
        assert _token_matches_crypto("ETH") is True
        assert _token_matches_crypto("WEATHER") is False

    def test_token_matches_asset(self) -> None:
        """Test _token_matches_asset function."""
        assert _token_matches_asset("BTC", "BTC") is True
        assert _token_matches_asset("BTCUSD", "BTC") is True
        assert _token_matches_asset("ETH", "BTC") is False

    def test_close_time_in_future(self) -> None:
        """Test _close_time_in_future function."""
        future_market = {"close_time": "2099-12-31T23:59:59Z"}
        past_market = {"close_time": "2020-01-01T00:00:00Z"}
        now_ts = 1735000000.0

        assert _close_time_in_future(future_market, now_ts) is True
        assert _close_time_in_future(past_market, now_ts) is False


class TestCreateEmptyStats:
    """Tests for _create_empty_stats function."""

    def test_returns_empty_stats(self) -> None:
        """Test returns empty stats dict."""
        stats = _create_empty_stats()

        assert stats["crypto_total"] == 0
        assert stats["crypto_kept"] == 0
        assert stats["weather_total"] == 0
        assert stats["weather_kept"] == 0
        assert stats["other_total"] == 0


class TestIsValidMarket:
    """Tests for _is_valid_market function."""

    def test_valid_market_with_ticker(self) -> None:
        """Test valid market with ticker."""
        market = {"ticker": "KXBTC-25JAN01"}

        assert _is_valid_market(market) is True

    def test_invalid_non_dict(self) -> None:
        """Test invalid non-dict market."""
        assert _is_valid_market("not a dict") is False
        assert _is_valid_market(123) is False
        assert _is_valid_market(None) is False

    def test_invalid_empty_ticker(self) -> None:
        """Test invalid market with empty ticker."""
        market = {"ticker": ""}

        assert _is_valid_market(market) is False

    def test_invalid_none_ticker(self) -> None:
        """Test invalid market with None ticker."""
        market = {"ticker": None}

        assert _is_valid_market(market) is False

    def test_invalid_missing_ticker(self) -> None:
        """Test invalid market without ticker."""
        market = {"category": "Weather"}

        assert _is_valid_market(market) is False


class TestIsWeatherMarket:
    """Tests for _is_weather_market function."""

    def test_weather_category(self) -> None:
        """Test Weather category returns True."""
        assert _is_weather_market("Weather", "SOMEMARKET") is True

    def test_climate_and_weather_category(self) -> None:
        """Test Climate and Weather category returns True."""
        assert _is_weather_market("Climate and Weather", "SOMEMARKET") is True

    def test_kxhigh_ticker(self) -> None:
        """Test KXHIGH ticker prefix returns True."""
        assert _is_weather_market("Other", "KXHIGHTEMP") is True

    def test_non_weather_market(self) -> None:
        """Test non-weather market returns False."""
        assert _is_weather_market("Crypto", "KXBTC-25JAN01") is False


class TestExtractWeatherStationToken:
    """Tests for _extract_weather_station_token function."""

    def test_extracts_station_token(self) -> None:
        """Test extracts station token from ticker."""
        result = _extract_weather_station_token("KXHIGHMIA-25JAN01")

        assert result == "MIA"

    def test_extracts_from_non_kxhigh_ticker(self) -> None:
        """Test extracts from non-KXHIGH ticker (takes chars after KXHIGH prefix)."""
        result = _extract_weather_station_token("KXMIA-25JAN01")

        # "KXMIA-25JAN01"[6:] = "25JAN01", split("-")[0] = "25JAN01"
        assert result == "25JAN01"

    def test_returns_none_for_empty_suffix(self) -> None:
        """Test returns None for empty suffix."""
        result = _extract_weather_station_token("KXHIGH")

        assert result is None


class TestPassesWeatherFilters:
    """Tests for _passes_weather_filters function."""

    def test_passes_with_valid_station(self) -> None:
        """Test passes with valid station token."""
        market = {"ticker": "KXHIGHMIA-25JAN01", "close_time": "2099-12-31T23:59:59Z"}
        now_ts = 1735000000.0
        weather_tokens = {"MIA", "JFK"}

        result = _passes_weather_filters(market, now_ts, weather_tokens)

        assert result is True

    def test_fails_with_invalid_station(self) -> None:
        """Test fails with invalid station token."""
        market = {"ticker": "KXHIGHABC-25JAN01", "close_time": "2099-12-31T23:59:59Z"}
        now_ts = 1735000000.0
        weather_tokens = {"MIA", "JFK"}

        result = _passes_weather_filters(market, now_ts, weather_tokens)

        assert result is False

    def test_fails_with_non_kxhigh_ticker(self) -> None:
        """Test fails with non-KXHIGH ticker."""
        market = {"ticker": "KXMIA-25JAN01", "close_time": "2099-12-31T23:59:59Z"}
        now_ts = 1735000000.0
        weather_tokens = {"MIA", "JFK"}

        result = _passes_weather_filters(market, now_ts, weather_tokens)

        assert result is False


class TestProcessMarketEntry:
    """Tests for _process_market_entry function."""

    def test_processes_crypto_market(self) -> None:
        """Test processes crypto market."""
        mock_validator = MagicMock()
        mock_validator.is_crypto_market.return_value = True
        mock_validator.passes_crypto_filters.return_value = True

        market = {"__category": "Crypto", "ticker": "KXBTC-25JAN01-T100000"}
        filtered: list[dict[str, object]] = []
        stats = _create_empty_stats()
        now_ts = 1735000000.0

        _process_market_entry(market, filtered, stats, now_ts, mock_validator, set())

        assert stats["crypto_total"] == 1
        assert stats["crypto_kept"] == 1
        assert len(filtered) == 1

    def test_processes_crypto_market_filtered_out(self) -> None:
        """Test crypto market filtered out."""
        mock_validator = MagicMock()
        mock_validator.is_crypto_market.return_value = True
        mock_validator.passes_crypto_filters.return_value = False

        market = {"__category": "Crypto", "ticker": "KXBTC-25JAN01-T100000"}
        filtered: list[dict[str, object]] = []
        stats = _create_empty_stats()
        now_ts = 1735000000.0

        _process_market_entry(market, filtered, stats, now_ts, mock_validator, set())

        assert stats["crypto_total"] == 1
        assert stats["crypto_kept"] == 0
        assert len(filtered) == 0

    def test_processes_weather_market(self) -> None:
        """Test processes weather market."""
        mock_validator = MagicMock()
        mock_validator.is_crypto_market.return_value = False

        market = {"__category": "Weather", "ticker": "KXHIGHMIA-25JAN01", "close_time": "2099-12-31T23:59:59Z"}
        filtered: list[dict[str, object]] = []
        stats = _create_empty_stats()
        now_ts = 1735000000.0
        weather_tokens = {"MIA"}

        _process_market_entry(market, filtered, stats, now_ts, mock_validator, weather_tokens)

        assert stats["weather_total"] == 1
        assert stats["weather_kept"] == 1
        assert len(filtered) == 1

    def test_processes_other_market(self) -> None:
        """Test processes other market type."""
        mock_validator = MagicMock()
        mock_validator.is_crypto_market.return_value = False

        market = {"__category": "Politics", "ticker": "ELECTION-25JAN01"}
        filtered: list[dict[str, object]] = []
        stats = _create_empty_stats()
        now_ts = 1735000000.0

        _process_market_entry(market, filtered, stats, now_ts, mock_validator, set())

        assert stats["other_total"] == 1
        assert len(filtered) == 0

    def test_handles_missing_ticker(self) -> None:
        """Test handles missing ticker."""
        mock_validator = MagicMock()
        mock_validator.is_crypto_market.return_value = False

        market = {"__category": "Other"}
        filtered: list[dict[str, object]] = []
        stats = _create_empty_stats()
        now_ts = 1735000000.0

        _process_market_entry(market, filtered, stats, now_ts, mock_validator, set())

        assert stats["other_total"] == 1


class TestCryptoMarketValidator:
    """Tests for CryptoMarketValidator class."""

    def test_is_crypto_market_by_ticker(self) -> None:
        """Test detects crypto market by ticker."""
        validator = CryptoMarketValidator()
        market = {"ticker": "KXBTC-25JAN01-T100000"}

        assert validator.is_crypto_market(market) is True

    def test_is_crypto_market_by_field(self) -> None:
        """Test detects crypto market by field."""
        validator = CryptoMarketValidator()
        market = {"ticker": "SOMEMARKET", "currency": "BTC"}

        assert validator.is_crypto_market(market) is True

    def test_is_not_crypto_market(self) -> None:
        """Test non-crypto market."""
        validator = CryptoMarketValidator()
        market = {"ticker": "KXMIA-25JAN01", "currency": "USD"}

        assert validator.is_crypto_market(market) is False

    def test_passes_crypto_filters_valid(self) -> None:
        """Test passes filters for valid crypto market."""
        validator = CryptoMarketValidator()
        market = {
            "ticker": "KXBTC-25JAN01-T100000",
            "close_time": "2099-12-31T23:59:59Z",
            "strike_type": "greater",
            "floor_strike": 100000,
        }
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is True

    def test_fails_crypto_filters_missing_ticker(self) -> None:
        """Test fails filters with missing ticker."""
        validator = CryptoMarketValidator()
        market: dict[str, object] = {"strike_type": "greater", "floor_strike": 100000}
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is False

    def test_fails_crypto_filters_no_crypto_asset(self) -> None:
        """Test fails filters without crypto asset in ticker."""
        validator = CryptoMarketValidator()
        market = {
            "ticker": "KXWEATHER-25JAN01",
            "close_time": "2099-12-31T23:59:59Z",
            "strike_type": "greater",
            "floor_strike": 100,
        }
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is False

    def test_fails_crypto_filters_no_month_code(self) -> None:
        """Test fails filters without month code."""
        validator = CryptoMarketValidator()
        market = {
            "ticker": "KXBTC-INVALID",
            "close_time": "2099-12-31T23:59:59Z",
            "strike_type": "greater",
            "floor_strike": 100000,
        }
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is False

    def test_fails_crypto_filters_past_close(self) -> None:
        """Test fails filters with past close time."""
        validator = CryptoMarketValidator()
        market = {
            "ticker": "KXBTC-25JAN01-T100000",
            "close_time": "2020-01-01T00:00:00Z",
            "strike_type": "greater",
            "floor_strike": 100000,
        }
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is False

    def test_fails_crypto_filters_invalid_strike_type(self) -> None:
        """Test fails filters with invalid strike type."""
        validator = CryptoMarketValidator()
        market = {
            "ticker": "KXBTC-25JAN01-T100000",
            "close_time": "2099-12-31T23:59:59Z",
            "strike_type": "invalid",
            "floor_strike": 100000,
        }
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is False

    def test_fails_crypto_filters_no_strike_bounds(self) -> None:
        """Test fails filters without strike bounds."""
        validator = CryptoMarketValidator()
        market = {
            "ticker": "KXBTC-25JAN01-T100000",
            "close_time": "2099-12-31T23:59:59Z",
            "strike_type": "greater",
        }
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is False

    def test_fails_crypto_filters_equal_strike_bounds(self) -> None:
        """Test fails filters with equal strike bounds."""
        validator = CryptoMarketValidator()
        market = {
            "ticker": "KXBTC-25JAN01-T100000",
            "close_time": "2099-12-31T23:59:59Z",
            "strike_type": "between",
            "floor_strike": 100000,
            "cap_strike": 100000,
        }
        now_ts = 1735000000.0

        assert validator.passes_crypto_filters(market, now_ts) is False

    def test_normalized_ticker_uppercase(self) -> None:
        """Test _normalized_ticker uppercases ticker."""
        validator = CryptoMarketValidator()
        market = {"ticker": "kxbtc-25jan01"}

        result = validator._normalized_ticker(market)

        assert result == "KXBTC-25JAN01"

    def test_normalized_ticker_empty(self) -> None:
        """Test _normalized_ticker with no ticker."""
        validator = CryptoMarketValidator()
        market: dict[str, object] = {}

        result = validator._normalized_ticker(market)

        assert result == ""

    def test_contains_crypto_asset(self) -> None:
        """Test _contains_crypto_asset."""
        validator = CryptoMarketValidator()

        assert validator._contains_crypto_asset("KXBTC-25JAN01") is True
        assert validator._contains_crypto_asset("KXETH-25JAN01") is True
        assert validator._contains_crypto_asset("KXMIA-25JAN01") is False

    def test_contains_month_code(self) -> None:
        """Test _contains_month_code."""
        validator = CryptoMarketValidator()

        assert validator._contains_month_code("KXBTC-25JAN01") is True
        assert validator._contains_month_code("KXBTC-INVALID") is False

    def test_has_valid_strike_type(self) -> None:
        """Test _has_valid_strike_type."""
        validator = CryptoMarketValidator()

        assert validator._has_valid_strike_type({"strike_type": "greater"}) is True
        assert validator._has_valid_strike_type({"strike_type": "invalid"}) is False
        assert validator._has_valid_strike_type({}) is False

    def test_has_valid_strike_bounds(self) -> None:
        """Test _has_valid_strike_bounds."""
        validator = CryptoMarketValidator()

        assert validator._has_valid_strike_bounds({"floor_strike": 100}) is True
        assert validator._has_valid_strike_bounds({"cap_strike": 200}) is True
        assert validator._has_valid_strike_bounds({"floor_strike": 100, "cap_strike": 200}) is True
        assert validator._has_valid_strike_bounds({}) is False
        assert validator._has_valid_strike_bounds({"floor_strike": 100, "cap_strike": 100}) is False


class TestMarketFilter:
    """Tests for MarketFilter class."""

    def test_init_stores_tokens(self) -> None:
        """Test initialization stores weather tokens."""
        tokens = {"MIA", "JFK"}
        filter_obj = MarketFilter(tokens)

        assert filter_obj._weather_station_tokens == tokens

    def test_filter_markets_empty(self) -> None:
        """Test filter_markets with empty list."""
        filter_obj = MarketFilter(set())

        filtered, stats = filter_obj.filter_markets([])

        assert filtered == []
        assert stats["crypto_total"] == 0
        assert stats["weather_total"] == 0

    def test_filter_markets_skips_invalid(self) -> None:
        """Test filter_markets skips invalid markets."""
        filter_obj = MarketFilter(set())
        markets = [
            {"ticker": ""},  # Invalid empty ticker
            "not a dict",  # Invalid non-dict
            {"no_ticker": True},  # Missing ticker
        ]

        filtered, stats = filter_obj.filter_markets(markets)

        assert filtered == []
        assert stats["crypto_total"] == 0
        assert stats["weather_total"] == 0
        assert stats["other_total"] == 0

    @patch("common.kalshi_catalog_helpers.market_filter.time.time")
    def test_filter_markets_crypto(self, mock_time: MagicMock) -> None:
        """Test filter_markets with crypto market."""
        mock_time.return_value = 1735000000.0
        filter_obj = MarketFilter(set())
        markets = [
            {
                "__category": "Crypto",
                "ticker": "KXBTC-25JAN01-T100000",
                "close_time": "2099-12-31T23:59:59Z",
                "strike_type": "greater",
                "floor_strike": 100000,
            }
        ]

        filtered, stats = filter_obj.filter_markets(markets)

        assert stats["crypto_total"] == 1
        assert stats["crypto_kept"] == 1
        assert len(filtered) == 1

    @patch("common.kalshi_catalog_helpers.market_filter.time.time")
    def test_filter_markets_weather(self, mock_time: MagicMock) -> None:
        """Test filter_markets with weather market."""
        mock_time.return_value = 1735000000.0
        filter_obj = MarketFilter({"MIA"})
        markets = [
            {
                "__category": "Weather",
                "ticker": "KXHIGHMIA-25JAN01",
                "close_time": "2099-12-31T23:59:59Z",
            }
        ]

        filtered, stats = filter_obj.filter_markets(markets)

        assert stats["weather_total"] == 1
        assert stats["weather_kept"] == 1
        assert len(filtered) == 1

    @patch("common.kalshi_catalog_helpers.market_filter.time.time")
    def test_filter_markets_other(self, mock_time: MagicMock) -> None:
        """Test filter_markets with other market type."""
        mock_time.return_value = 1735000000.0
        filter_obj = MarketFilter(set())
        markets = [{"__category": "Politics", "ticker": "ELECTION-2025"}]

        filtered, stats = filter_obj.filter_markets(markets)

        assert stats["other_total"] == 1
        assert len(filtered) == 0
