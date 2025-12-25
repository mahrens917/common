from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional, Sequence, cast

if TYPE_CHECKING:
    from common.trade_visualizer import TradeVisualizer

logger = logging.getLogger(__name__)


async def annotate_trades_if_needed(
    *,
    ax,
    station_icao: Optional[str],
    naive_timestamps: Optional[Sequence[datetime]],
    plot_timestamps: Sequence[datetime],
    is_temperature_chart: bool,
    kalshi_strikes: Optional[Sequence[float]],
    trade_visualizer_cls: Optional[type[TradeVisualizer]] = None,
) -> None:
    """
    Overlay trade shading on a temperature chart when Kalshi strike data is available.

    Args:
        ax: Matplotlib axis to annotate.
        station_icao: Weather station identifier.
        naive_timestamps: Precomputed naive timestamps aligned with the chart data.
        plot_timestamps: Timestamps used for plotting (typically localized for display).
        is_temperature_chart: Indicates whether the chart represents temperature data.
        kalshi_strikes: Configured Kalshi strike levels; required to enable shading.
    """
    if not _should_annotate(station_icao, is_temperature_chart, kalshi_strikes, naive_timestamps):
        return

    assert station_icao is not None
    assert naive_timestamps is not None
    assert kalshi_strikes is not None

    await _render_trade_visualizations(
        ax=ax,
        station_icao=station_icao,
        naive_timestamps=naive_timestamps,
        plot_timestamps=plot_timestamps,
        kalshi_strikes=kalshi_strikes,
        trade_visualizer_cls=trade_visualizer_cls,
    )


def _should_annotate(
    station_icao: Optional[str],
    is_temperature_chart: bool,
    kalshi_strikes: Optional[Sequence[float]],
    naive_timestamps: Optional[Sequence[datetime]],
) -> bool:
    if not station_icao:
        return False
    if not (is_temperature_chart and kalshi_strikes and naive_timestamps):
        return False
    return True


async def _render_trade_visualizations(
    *,
    ax,
    station_icao: str,
    naive_timestamps: Sequence[datetime],
    plot_timestamps: Sequence[datetime],
    kalshi_strikes: Sequence[float],
    trade_visualizer_cls: Optional[type[TradeVisualizer]],
) -> None:
    trade_visualizer: Optional[TradeVisualizer] = None
    try:
        trade_visualizer = await _initialize_visualizer(trade_visualizer_cls)
        if trade_visualizer is None:
            logger.warning("Failed to initialize trade visualizer for %s", station_icao)
            return

        timestamps_to_use = list(naive_timestamps)
        strike_levels = list(kalshi_strikes)
        trade_shadings = await trade_visualizer.get_trade_shadings_for_station(
            station_icao,
            timestamps_to_use[0],
            timestamps_to_use[-1],
            timestamps_to_use,
            strike_levels,
        )
        _apply_trade_shadings(ax, trade_visualizer, trade_shadings, plot_timestamps, station_icao)
    except asyncio.CancelledError:
        raise
    except (OSError, RuntimeError, ValueError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        logger.exception("Failed to add trade visualization for %s", station_icao)
    finally:
        await _close_visualizer(trade_visualizer, station_icao)


async def _initialize_visualizer(
    trade_visualizer_cls: Optional[type[TradeVisualizer]],
) -> Optional[TradeVisualizer]:
    from common.trade_visualizer import TradeVisualizer as TradeVisualizerCls
    from common.trade_visualizer import (
        create_trade_visualizer,
    )

    visualizer_cls = trade_visualizer_cls or TradeVisualizerCls
    visualizer_factory = cast(Callable[[], TradeVisualizer], visualizer_cls)
    try:
        visualizer = visualizer_factory()
    except TypeError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        visualizer = create_trade_visualizer()
    except (ValueError, AttributeError, RuntimeError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        # Visualizer instantiation failed - charts will be disabled
        return None
    try:
        if await visualizer.initialize():
            return visualizer
    except (OSError, RuntimeError, ValueError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
        # Visualizer initialization failed - charts will be disabled
        return None
    return None


def _apply_trade_shadings(
    ax,
    visualizer: TradeVisualizer,
    trade_shadings,
    plot_timestamps: Sequence[datetime],
    station_icao: str,
) -> None:
    if not trade_shadings:
        return
    visualizer.apply_trade_shadings_to_chart(ax, trade_shadings, list(plot_timestamps))
    logger.info(
        "🎯 Added %d trade visualizations to %s chart",
        len(trade_shadings),
        station_icao,
    )


async def _close_visualizer(trade_visualizer: Optional[TradeVisualizer], station_icao: str) -> None:
    if trade_visualizer is None or not hasattr(trade_visualizer, "close"):
        return
    try:
        await trade_visualizer.close()
    except (
        RuntimeError,
        ValueError,
        TypeError,
    ) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.debug("Trade visualizer cleanup failed for %s: %s", station_icao, exc)
