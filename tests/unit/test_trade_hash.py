"""Tests for deterministic trade hash and timestamp normalizer."""

from __future__ import annotations

import pytest

from common.trade_hash import make_kalshi_trade_hash, ts_to_unix_seconds


class TestTsToUnixSeconds:
    """Tests for ts_to_unix_seconds."""

    def test_iso_z_suffix(self) -> None:
        assert ts_to_unix_seconds("2024-01-01T00:00:00Z") == 1704067200

    def test_iso_offset_suffix(self) -> None:
        assert ts_to_unix_seconds("2024-01-01T00:00:00+00:00") == 1704067200

    def test_unix_seconds_int(self) -> None:
        assert ts_to_unix_seconds(1704067200) == 1704067200

    def test_unix_seconds_float(self) -> None:
        assert ts_to_unix_seconds(1704067200.5) == 1704067200

    def test_unix_milliseconds(self) -> None:
        assert ts_to_unix_seconds(1704067200000) == 1704067200

    def test_consistent_across_formats(self) -> None:
        """ISO string, seconds int, and milliseconds int all produce the same result."""
        iso = ts_to_unix_seconds("2024-01-01T00:00:00Z")
        sec = ts_to_unix_seconds(1704067200)
        ms = ts_to_unix_seconds(1704067200000)
        assert iso == sec == ms == 1704067200


class TestMakeKalshiTradeHash:
    """Tests for make_kalshi_trade_hash."""

    def test_deterministic(self) -> None:
        """Same inputs always produce the same hash."""
        h1 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        h2 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        assert h1 == h2

    def test_length_is_16_hex(self) -> None:
        h = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        assert len(h) == 16
        int(h, 16)  # must be valid hex

    def test_different_ticker_produces_different_hash(self) -> None:
        h1 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        h2 = make_kalshi_trade_hash("TICKER-B", "yes", 65, 10, 1704067200)
        assert h1 != h2

    def test_different_side_produces_different_hash(self) -> None:
        h1 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        h2 = make_kalshi_trade_hash("TICKER-A", "no", 65, 10, 1704067200)
        assert h1 != h2

    def test_different_price_produces_different_hash(self) -> None:
        h1 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        h2 = make_kalshi_trade_hash("TICKER-A", "yes", 66, 10, 1704067200)
        assert h1 != h2

    def test_different_count_produces_different_hash(self) -> None:
        h1 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        h2 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 11, 1704067200)
        assert h1 != h2

    def test_different_ts_produces_different_hash(self) -> None:
        h1 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067200)
        h2 = make_kalshi_trade_hash("TICKER-A", "yes", 65, 10, 1704067201)
        assert h1 != h2


class TestEndToEnd:
    """Test hash consistency when timestamp normalization is combined with hash generation."""

    def test_rest_and_ws_produce_same_hash(self) -> None:
        """REST API (ISO string) and WebSocket (ms int) produce the same trade hash."""
        rest_ts = ts_to_unix_seconds("2024-01-15T10:30:00Z")
        ws_ts = ts_to_unix_seconds(1705314600000)
        rest_hash = make_kalshi_trade_hash("MKT-123", "yes", 55, 5, rest_ts)
        ws_hash = make_kalshi_trade_hash("MKT-123", "yes", 55, 5, ws_ts)
        assert rest_hash == ws_hash
