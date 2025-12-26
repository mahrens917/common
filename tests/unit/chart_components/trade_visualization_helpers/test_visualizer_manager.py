"""Tests for visualizer_manager module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_components.trade_visualization_helpers.visualizer_manager import (
    VisualizerManager,
)


@pytest.fixture
def mock_visualizer_cls() -> MagicMock:
    """Create a mock visualizer class."""
    mock_instance = MagicMock()
    mock_instance.initialize = AsyncMock(return_value=True)
    mock_instance.get_trade_shadings_for_station = AsyncMock(return_value=[])
    mock_instance.apply_trade_shadings_to_chart = MagicMock()
    mock_instance.close = AsyncMock()

    cls = MagicMock(return_value=mock_instance)
    return cls


class TestVisualizerManager:
    """Tests for VisualizerManager class."""

    def test_init(self, mock_visualizer_cls: MagicMock) -> None:
        """Test VisualizerManager initialization."""
        manager = VisualizerManager(mock_visualizer_cls)
        assert manager._visualizer_cls is mock_visualizer_cls
        assert manager._visualizer is None

    @pytest.mark.asyncio
    async def test_visualize_trades_success_no_shadings(self, mock_visualizer_cls: MagicMock) -> None:
        """Test visualize_trades with no shadings returned."""
        manager = VisualizerManager(mock_visualizer_cls)
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0]

        await manager.visualize_trades(mock_ax, "KJFK", timestamps, timestamps, strikes)

        mock_visualizer_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_visualize_trades_with_shadings(self, mock_visualizer_cls: MagicMock) -> None:
        """Test visualize_trades applies shadings when returned."""
        mock_instance = mock_visualizer_cls.return_value
        mock_instance.get_trade_shadings_for_station = AsyncMock(return_value=[{"shading": 1}])

        manager = VisualizerManager(mock_visualizer_cls)
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0]

        await manager.visualize_trades(mock_ax, "KJFK", timestamps, timestamps, strikes)

        mock_instance.apply_trade_shadings_to_chart.assert_called_once()

    @pytest.mark.asyncio
    async def test_visualize_trades_init_fails(self, mock_visualizer_cls: MagicMock) -> None:
        """Test visualize_trades when initialization fails."""
        mock_instance = mock_visualizer_cls.return_value
        mock_instance.initialize = AsyncMock(return_value=False)

        manager = VisualizerManager(mock_visualizer_cls)
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0]

        await manager.visualize_trades(mock_ax, "KJFK", timestamps, timestamps, strikes)

        mock_instance.get_trade_shadings_for_station.assert_not_called()

    @pytest.mark.asyncio
    async def test_visualize_trades_handles_exception(self, mock_visualizer_cls: MagicMock) -> None:
        """Test visualize_trades handles exceptions gracefully."""
        mock_instance = mock_visualizer_cls.return_value
        mock_instance.get_trade_shadings_for_station = AsyncMock(side_effect=ValueError("Error"))

        manager = VisualizerManager(mock_visualizer_cls)
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0]

        await manager.visualize_trades(mock_ax, "KJFK", timestamps, timestamps, strikes)

    @pytest.mark.asyncio
    async def test_cleanup_visualizer_calls_close(self, mock_visualizer_cls: MagicMock) -> None:
        """Test that cleanup calls close on visualizer."""
        mock_instance = mock_visualizer_cls.return_value

        manager = VisualizerManager(mock_visualizer_cls)
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0]

        await manager.visualize_trades(mock_ax, "KJFK", timestamps, timestamps, strikes)

        mock_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_close_exception(self, mock_visualizer_cls: MagicMock) -> None:
        """Test cleanup handles close exceptions."""
        mock_instance = mock_visualizer_cls.return_value
        mock_instance.close = AsyncMock(side_effect=RuntimeError("Close failed"))

        manager = VisualizerManager(mock_visualizer_cls)
        mock_ax = MagicMock()
        timestamps = [datetime(2024, 1, 1, 12, 0)]
        strikes = [70.0]

        await manager.visualize_trades(mock_ax, "KJFK", timestamps, timestamps, strikes)
