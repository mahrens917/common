"""Tests for common.config.market_manifest module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from common.config.market_manifest import (
    _decode_key,
    _default_station_flags,
    _determine_horizon,
    _extract_ticker,
    _parse_expiry_date,
    _resolve_station_market,
    build_market_manifest,
)
from common.redis_schema.markets import KalshiMarketCategory


class TestParseExpiryDate:
    """Tests for _parse_expiry_date."""

    def test_valid_token(self):
        result = _parse_expiry_date("26MAR14")
        assert result == datetime(2026, 3, 14, tzinfo=timezone.utc)

    def test_token_with_time_suffix(self):
        result = _parse_expiry_date("26MAR14T120000")
        assert result == datetime(2026, 3, 14, tzinfo=timezone.utc)

    def test_short_token_returns_none(self):
        assert _parse_expiry_date("26MA") is None

    def test_invalid_month_returns_none(self):
        assert _parse_expiry_date("26XYZ14") is None

    def test_invalid_day_returns_none(self):
        assert _parse_expiry_date("26MAR99") is None


class TestDetermineHorizon:
    """Tests for _determine_horizon."""

    def test_today_returns_zero(self):
        today = datetime.now(timezone.utc).replace(hour=12, minute=0)
        assert _determine_horizon(today) == 0

    def test_tomorrow_returns_one(self):
        tomorrow = datetime.now(timezone.utc).replace(hour=12, minute=0) + timedelta(days=1)
        assert _determine_horizon(tomorrow) == 1

    def test_future_returns_none(self):
        future = datetime.now(timezone.utc) + timedelta(days=5)
        assert _determine_horizon(future) is None


class TestDecodeKey:
    """Tests for _decode_key."""

    def test_string_passthrough(self):
        assert _decode_key("markets:kalshi:weather:TICK") == "markets:kalshi:weather:TICK"

    def test_bytes_decoded(self):
        assert _decode_key(b"markets:kalshi:weather:TICK") == "markets:kalshi:weather:TICK"


class TestExtractTicker:
    """Tests for _extract_ticker."""

    def test_valid_key(self):
        assert _extract_ticker("markets:kalshi:weather:KXHIGH-KDCA-26MAR14") == "KXHIGH-KDCA-26MAR14"

    def test_too_few_parts(self):
        assert _extract_ticker("markets:kalshi") is None

    def test_too_many_parts(self):
        assert _extract_ticker("a:b:c:d:e") is None


class TestDefaultStationFlags:
    """Tests for _default_station_flags."""

    def test_returns_all_false(self):
        flags = _default_station_flags()
        assert flags == {"high_h0": False, "high_h1": False, "low_h0": False, "low_h1": False}


class TestResolveStationMarket:
    """Tests for _resolve_station_market."""

    def test_non_weather_returns_none(self):
        with patch("common.config.market_manifest._classify_kalshi_ticker") as mock:
            mock.return_value = (KalshiMarketCategory.CUSTOM, None, None)
            assert _resolve_station_market("TICK", {}) is None

    def test_missing_underlying_returns_none(self):
        with patch("common.config.market_manifest._classify_kalshi_ticker") as mock:
            mock.return_value = (KalshiMarketCategory.WEATHER, None, "26MAR14")
            assert _resolve_station_market("TICK", {}) is None

    def test_unknown_underlying_returns_none(self):
        with patch("common.config.market_manifest._classify_kalshi_ticker") as mock:
            mock.return_value = (KalshiMarketCategory.WEATHER, "UNKNOWN", "26MAR14")
            assert _resolve_station_market("TICK", {}) is None

    def test_invalid_expiry_returns_none(self):
        with patch("common.config.market_manifest._classify_kalshi_ticker") as mock:
            mock.return_value = (KalshiMarketCategory.WEATHER, "KDCA", "bad")
            assert _resolve_station_market("TICK", {"KDCA": "KDCA"}) is None

    def test_out_of_range_horizon_returns_none(self):
        with patch("common.config.market_manifest._classify_kalshi_ticker") as mock:
            mock.return_value = (KalshiMarketCategory.WEATHER, "KDCA", "30DEC31")
            assert _resolve_station_market("KXHIGH-KDCA-30DEC31", {"KDCA": "KDCA"}) is None

    def test_valid_high_ticker(self):
        today = datetime.now(timezone.utc)
        token = today.strftime("%y") + today.strftime("%b").upper() + today.strftime("%d")
        ticker = f"KXHIGH-KDCA-{token}"
        with patch("common.config.market_manifest._classify_kalshi_ticker") as mock:
            mock.return_value = (KalshiMarketCategory.WEATHER, "KDCA", token)
            result = _resolve_station_market(ticker, {"KDCA": "KDCA"})
            assert result == ("KDCA", "high_h0")

    def test_valid_low_ticker(self):
        today = datetime.now(timezone.utc)
        token = today.strftime("%y") + today.strftime("%b").upper() + today.strftime("%d")
        ticker = f"KXLOW-KDCA-{token}"
        with patch("common.config.market_manifest._classify_kalshi_ticker") as mock:
            mock.return_value = (KalshiMarketCategory.WEATHER, "KDCA", token)
            result = _resolve_station_market(ticker, {"KDCA": "KDCA"})
            assert result == ("KDCA", "low_h0")


class TestBuildMarketManifest:
    """Tests for build_market_manifest."""

    @patch("common.config.market_manifest._resolve_station_market")
    @patch("common.config.market_manifest.load_market_code_mapping")
    def test_empty_keys(self, mock_mapping, mock_resolve):
        mock_mapping.return_value = {}
        result = build_market_manifest([])
        assert "generated_at" in result
        assert result["stations"] == {}

    @patch("common.config.market_manifest._resolve_station_market")
    @patch("common.config.market_manifest.load_market_code_mapping")
    def test_valid_key_creates_station(self, mock_mapping, mock_resolve):
        mock_mapping.return_value = {"KDCA": "KDCA"}
        mock_resolve.return_value = ("KDCA", "high_h0")

        result = build_market_manifest(["markets:kalshi:weather:KXHIGH-KDCA-26MAR15"])

        assert "KDCA" in result["stations"]
        assert result["stations"]["KDCA"]["high_h0"] is True

    @patch("common.config.market_manifest._resolve_station_market")
    @patch("common.config.market_manifest.load_market_code_mapping")
    def test_invalid_key_format_skipped(self, mock_mapping, mock_resolve):
        mock_mapping.return_value = {}
        result = build_market_manifest(["bad_key"])
        assert result["stations"] == {}
        mock_resolve.assert_not_called()

    @patch("common.config.market_manifest._resolve_station_market")
    @patch("common.config.market_manifest.load_market_code_mapping")
    def test_unresolvable_ticker_skipped(self, mock_mapping, mock_resolve):
        mock_mapping.return_value = {}
        mock_resolve.return_value = None

        result = build_market_manifest(["markets:kalshi:weather:UNKNOWN"])
        assert result["stations"] == {}

    @patch("common.config.market_manifest._resolve_station_market")
    @patch("common.config.market_manifest.load_market_code_mapping")
    def test_bytes_keys_decoded(self, mock_mapping, mock_resolve):
        mock_mapping.return_value = {}
        mock_resolve.return_value = ("KJFK", "low_h1")

        result = build_market_manifest([b"markets:kalshi:weather:KXLOW-KJFK-26MAR16"])

        assert "KJFK" in result["stations"]

    @patch("common.config.market_manifest._resolve_station_market")
    @patch("common.config.market_manifest.load_market_code_mapping")
    def test_stations_sorted(self, mock_mapping, mock_resolve):
        mock_mapping.return_value = {}
        call_count = {"n": 0}

        def side_effect(ticker, mapping):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return ("KORD", "high_h0")
            return ("KATL", "low_h0")

        mock_resolve.side_effect = side_effect

        result = build_market_manifest(
            [
                "markets:kalshi:weather:T1",
                "markets:kalshi:weather:T2",
            ]
        )

        station_keys = list(result["stations"].keys())
        assert station_keys == ["KATL", "KORD"]
