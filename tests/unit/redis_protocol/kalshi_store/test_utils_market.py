import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.orderbook_parser import extract_orderbook_sizes
from common.redis_protocol.kalshi_store.utils_market import (
    _coerce_strike_bounds,
    _normalise_timestamp_numeric,
    _normalise_timestamp_string,
    _parse_market_metadata,
    _resolve_market_strike,
    _resolve_strike_from_bounds,
    normalise_trade_timestamp,
)


class TestUtilsMarket:
    def testnormalise_trade_timestamp_valid_string(self):
        iso = "2023-01-01T12:00:00Z"
        result = normalise_trade_timestamp(iso)
        assert result == "2023-01-01T12:00:00+00:00"

    def testnormalise_trade_timestamp_valid_numeric(self):
        ts = 1672574400.0  # 2023-01-01 12:00:00 UTC
        result = normalise_trade_timestamp(ts)
        assert result == "2023-01-01T12:00:00+00:00"

    def testnormalise_trade_timestamp_invalid(self):
        assert normalise_trade_timestamp("invalid") == ""
        assert normalise_trade_timestamp(None) == ""

    def test_normalise_timestamp_string_timezone(self):
        iso = "2023-01-01T12:00:00"
        # Should assume UTC
        result = _normalise_timestamp_string(iso)
        assert result == "2023-01-01T12:00:00+00:00"

    def test_normalise_timestamp_numeric_units(self):
        # Milliseconds (2023)
        ts_sec_2023 = 1672574400.0
        ts_ms = ts_sec_2023 * 1000
        expected_2023 = "2023-01-01T12:00:00+00:00"
        assert _normalise_timestamp_numeric(ts_ms) == expected_2023

        # Microseconds (1990 - to fit within logic thresholds)
        ts_sec_1990 = 631152000.0
        ts_us = ts_sec_1990 * 1000000
        expected_1990 = "1990-01-01T00:00:00+00:00"
        assert _normalise_timestamp_numeric(ts_us) == expected_1990

        # Nanoseconds (2023)
        ts_ns = ts_sec_2023 * 1000000000
        assert _normalise_timestamp_numeric(ts_ns) == expected_2023

    def test_parse_market_metadata_success(self):
        data = {"metadata": json.dumps({"key": "value"}).encode("utf-8")}
        result = _parse_market_metadata("ticker", data)
        assert result == {"key": "value"}

    def test_parse_market_metadata_missing(self):
        assert _parse_market_metadata("ticker", {}) is None
        assert _parse_market_metadata("ticker", None) is None

    def test_parse_market_metadata_invalid_json(self):
        data = {"metadata": b"invalid"}
        result = _parse_market_metadata("ticker", data)
        assert result is None

    def test_coerce_strike_bounds(self):
        assert _coerce_strike_bounds("10.5", 20) == (10.5, 20.0)
        assert _coerce_strike_bounds(None, "") == (None, None)
        assert _coerce_strike_bounds("invalid", 20) == (None, None)

    def test_resolve_strike_from_bounds(self):
        assert _resolve_strike_from_bounds("between", 10, 20) == 15.0
        assert _resolve_strike_from_bounds("greater", 10, None) == 10.0
        assert _resolve_strike_from_bounds("less", None, 20) == 20.0
        assert _resolve_strike_from_bounds("unknown", 10, 20) is None
        assert _resolve_strike_from_bounds("between", None, 20) is None

    def test_resolve_market_strike(self):
        metadata = {"strike_type": "between", "floor_strike": "10", "cap_strike": "20"}
        assert _resolve_market_strike(metadata) == 15.0

    def test_extract_orderbook_sizes(self):
        market_data = {"orderbook": '{"yes_bids": {"50": 10}, "yes_asks": {"55": 20}}'}
        bid_size, ask_size = extract_orderbook_sizes("ticker", market_data)
        assert bid_size == 10.0
        assert ask_size == 20.0
