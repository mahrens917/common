"""Tests for precondition_checker module."""

from datetime import datetime

from common.chart_components.trade_visualization_helpers.precondition_checker import (
    should_annotate_trades,
)


class TestShouldAnnotateTrades:
    """Tests for should_annotate_trades function."""

    def test_returns_true_when_all_conditions_met(self) -> None:
        """Test returns True when all conditions are satisfied."""
        result = should_annotate_trades(
            station_icao="KJFK",
            is_temperature_chart=True,
            kalshi_strikes=[70.0, 75.0],
            naive_timestamps=[datetime(2024, 1, 1, 12, 0)],
        )
        assert result is True

    def test_returns_false_when_station_icao_is_none(self) -> None:
        """Test returns False when station_icao is None."""
        result = should_annotate_trades(
            station_icao=None,
            is_temperature_chart=True,
            kalshi_strikes=[70.0],
            naive_timestamps=[datetime(2024, 1, 1)],
        )
        assert result is False

    def test_returns_false_when_station_icao_is_empty(self) -> None:
        """Test returns False when station_icao is empty string."""
        result = should_annotate_trades(
            station_icao="",
            is_temperature_chart=True,
            kalshi_strikes=[70.0],
            naive_timestamps=[datetime(2024, 1, 1)],
        )
        assert result is False

    def test_returns_false_when_not_temperature_chart(self) -> None:
        """Test returns False when is_temperature_chart is False."""
        result = should_annotate_trades(
            station_icao="KJFK",
            is_temperature_chart=False,
            kalshi_strikes=[70.0],
            naive_timestamps=[datetime(2024, 1, 1)],
        )
        assert result is False

    def test_returns_false_when_kalshi_strikes_is_none(self) -> None:
        """Test returns False when kalshi_strikes is None."""
        result = should_annotate_trades(
            station_icao="KJFK",
            is_temperature_chart=True,
            kalshi_strikes=None,
            naive_timestamps=[datetime(2024, 1, 1)],
        )
        assert result is False

    def test_returns_false_when_kalshi_strikes_is_empty(self) -> None:
        """Test returns False when kalshi_strikes is empty."""
        result = should_annotate_trades(
            station_icao="KJFK",
            is_temperature_chart=True,
            kalshi_strikes=[],
            naive_timestamps=[datetime(2024, 1, 1)],
        )
        assert result is False

    def test_returns_false_when_naive_timestamps_is_none(self) -> None:
        """Test returns False when naive_timestamps is None."""
        result = should_annotate_trades(
            station_icao="KJFK",
            is_temperature_chart=True,
            kalshi_strikes=[70.0],
            naive_timestamps=None,
        )
        assert result is False

    def test_returns_false_when_naive_timestamps_is_empty(self) -> None:
        """Test returns False when naive_timestamps is empty."""
        result = should_annotate_trades(
            station_icao="KJFK",
            is_temperature_chart=True,
            kalshi_strikes=[70.0],
            naive_timestamps=[],
        )
        assert result is False
