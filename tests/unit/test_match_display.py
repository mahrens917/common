"""Tests for scripts/match_display.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from scripts.match_display import print_field_extraction_results, print_field_match_results, print_near_misses


class TestPrintFieldExtractionResults:
    """Tests for print_field_extraction_results."""

    def test_prints_summary(self, capsys):
        fields = [MagicMock(category="crypto", underlying="ETH", floor_strike=100.0, cap_strike=None)]
        print_field_extraction_results(fields)
        captured = capsys.readouterr()
        assert "EXTRACTED FIELDS FOR 1 POLY MARKETS" in captured.out
        assert "crypto" in captured.out
        assert "ETH" in captured.out

    def test_empty_fields(self, capsys):
        print_field_extraction_results([])
        captured = capsys.readouterr()
        assert "EXTRACTED FIELDS FOR 0 POLY MARKETS" in captured.out


class TestPrintFieldMatchResults:
    """Tests for print_field_match_results."""

    def test_prints_matches(self, capsys):
        fields = MagicMock(category="crypto", underlying="ETH", floor_strike=100.0, cap_strike=None)
        kalshi = {
            "event_title": "ETH Daily",
            "market_ticker": "KXETHD",
            "floor_strike": "100",
            "cap_strike": None,
            "close_time": "2025-01-15",
        }
        poly = {"title": "Poly ETH", "end_date": "2025-01-15"}
        print_field_match_results([(kalshi, fields, poly)])
        captured = capsys.readouterr()
        assert "FIELD-BASED MATCHES: 1" in captured.out
        assert "ETH Daily" in captured.out

    def test_empty_matches(self, capsys):
        print_field_match_results([])
        captured = capsys.readouterr()
        assert "FIELD-BASED MATCHES: 0" in captured.out


class TestPrintNearMisses:
    """Tests for print_near_misses."""

    def test_empty_near_misses(self, capsys):
        print_near_misses([])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_prints_near_misses(self, capsys):
        fields = MagicMock(category="crypto", underlying="ETH", floor_strike=100.0, cap_strike=None)
        nm = {
            "kalshi": {
                "event_title": "ETH",
                "market_ticker": "KXETHD",
                "floor_strike": "100",
                "cap_strike": None,
                "close_time": "2025-01-15",
            },
            "fields": fields,
            "poly": {"title": "Poly", "end_date": "2025-01-15"},
            "expiry_delta_min": 5.0,
            "floor_pct": 0.05,
            "cap_pct": None,
        }
        print_near_misses([nm])
        captured = capsys.readouterr()
        assert "NEAR MISSES" in captured.out
        assert "expiry delta=5.0min" in captured.out
