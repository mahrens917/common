"""Manage trade visualizer lifecycle and rendering."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional, Sequence

if TYPE_CHECKING:
    from common.trade_visualizer import TradeVisualizer

logger = logging.getLogger(__name__)


class VisualizerManager:
    """Manages trade visualizer lifecycle."""

    def __init__(self, visualizer_cls: Callable[[], TradeVisualizer]):
        """Initialize with visualizer class."""
        self._visualizer_cls: Callable[[], TradeVisualizer] = visualizer_cls
        self._visualizer: Optional[TradeVisualizer] = None

    async def visualize_trades(
        self,
        ax,
        station_icao: str,
        naive_timestamps: Sequence[datetime],
        plot_timestamps: Sequence[datetime],
        kalshi_strikes: Sequence[float],
    ) -> None:
        """Visualize trades on chart."""
        try:
            await self._initialize_visualizer(station_icao)
            visualizer = self._visualizer
            if visualizer is None:
                return
            visualizer_instance: TradeVisualizer = visualizer

            trade_shadings = await self._fetch_trade_shadings(visualizer_instance, station_icao, naive_timestamps, kalshi_strikes)

            if trade_shadings:
                self._apply_shadings(ax, visualizer_instance, trade_shadings, plot_timestamps, station_icao)
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError, ValueError):
            logger.exception("Failed to add trade visualization for %s", station_icao)
        finally:
            await self._cleanup_visualizer(station_icao)

    async def _initialize_visualizer(self, station_icao: str) -> None:
        """Initialize the visualizer."""
        self._visualizer = self._visualizer_cls()
        if not await self._visualizer.initialize():
            logger.warning("Failed to initialize trade visualizer for %s", station_icao)
            self._visualizer = None

    async def _fetch_trade_shadings(
        self,
        visualizer: TradeVisualizer,
        station_icao: str,
        naive_timestamps: Sequence[datetime],
        kalshi_strikes: Sequence[float],
    ):
        """Fetch trade shadings for station."""
        timestamps_to_use = list(naive_timestamps)
        strike_levels = list(kalshi_strikes)
        start_time = timestamps_to_use[0]
        end_time = timestamps_to_use[-1]

        return await visualizer.get_trade_shadings_for_station(station_icao, start_time, end_time, timestamps_to_use, strike_levels)

    def _apply_shadings(
        self,
        ax,
        visualizer: TradeVisualizer,
        trade_shadings,
        plot_timestamps: Sequence[datetime],
        station_icao: str,
    ) -> None:
        """Apply trade shadings to chart."""
        visualizer.apply_trade_shadings_to_chart(ax, trade_shadings, list(plot_timestamps))
        logger.info("<¯ Added %d trade visualizations to %s chart", len(trade_shadings), station_icao)

    async def _cleanup_visualizer(self, station_icao: str) -> None:
        """Clean up visualizer resources."""
        if self._visualizer is not None and hasattr(self._visualizer, "close"):
            try:
                await self._visualizer.close()
            except (RuntimeError, ValueError, TypeError, OSError) as exc:
                logger.debug("Trade visualizer cleanup failed for %s: %s", station_icao, exc)
