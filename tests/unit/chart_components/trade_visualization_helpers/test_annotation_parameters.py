"""Tests for annotation_parameters module."""

from datetime import datetime
from unittest.mock import MagicMock

from common.chart_components.trade_visualization_helpers.annotation_parameters import (
    TradeAnnotationParameters,
    TradeShadingParameters,
)


class TestTradeAnnotationParameters:
    """Tests for TradeAnnotationParameters dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """Test creating TradeAnnotationParameters with all fields."""
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0, 75.0]

        params = TradeAnnotationParameters(
            ax=mock_ax,
            station_icao="KJFK",
            naive_timestamps=timestamps,
            plot_timestamps=timestamps,
            is_temperature_chart=True,
            kalshi_strikes=strikes,
            trade_visualizer_cls=MagicMock,
        )

        assert params.ax is mock_ax
        assert params.station_icao == "KJFK"
        assert params.naive_timestamps == timestamps
        assert params.is_temperature_chart is True
        assert params.kalshi_strikes == strikes

    def test_creation_with_optional_none(self) -> None:
        """Test creating TradeAnnotationParameters with optional fields as None."""
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1)]

        params = TradeAnnotationParameters(
            ax=mock_ax,
            station_icao=None,
            naive_timestamps=None,
            plot_timestamps=timestamps,
            is_temperature_chart=False,
            kalshi_strikes=None,
        )

        assert params.station_icao is None
        assert params.naive_timestamps is None
        assert params.kalshi_strikes is None
        assert params.trade_visualizer_cls is None

    def test_frozen(self) -> None:
        """Test that TradeAnnotationParameters is frozen."""
        params = TradeAnnotationParameters(
            ax=MagicMock(),
            station_icao="KJFK",
            naive_timestamps=[datetime(2024, 1, 1)],
            plot_timestamps=[datetime(2024, 1, 1)],
            is_temperature_chart=True,
            kalshi_strikes=[70.0],
        )
        try:
            params.station_icao = "KORD"
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass


class TestTradeShadingParameters:
    """Tests for TradeShadingParameters dataclass."""

    def test_creation(self) -> None:
        """Test creating TradeShadingParameters."""
        mock_visualizer = MagicMock()
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0, 75.0]

        params = TradeShadingParameters(
            trade_visualizer=mock_visualizer,
            ax=mock_ax,
            station_icao="KORD",
            naive_timestamps=timestamps,
            plot_timestamps=timestamps,
            kalshi_strikes=strikes,
        )

        assert params.trade_visualizer is mock_visualizer
        assert params.ax is mock_ax
        assert params.station_icao == "KORD"
        assert params.naive_timestamps == timestamps
        assert params.kalshi_strikes == strikes

    def test_frozen(self) -> None:
        """Test that TradeShadingParameters is frozen."""
        params = TradeShadingParameters(
            trade_visualizer=MagicMock(),
            ax=MagicMock(),
            station_icao="KJFK",
            naive_timestamps=[datetime(2024, 1, 1)],
            plot_timestamps=[datetime(2024, 1, 1)],
            kalshi_strikes=[70.0],
        )
        try:
            params.station_icao = "KORD"
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass
