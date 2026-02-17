from __future__ import annotations

"""Helper functions for ShadingBuilder."""


import logging
from datetime import datetime
from typing import List, Optional, Tuple

from common.data_models.trade_record import TradeRecord, TradeSide

logger = logging.getLogger(__name__)

TimeWindow = Optional[Tuple[datetime, datetime]]


def find_next_strike(trade_price: float, kalshi_strikes: List[float]) -> float:
    """Find next strike above trade price."""
    for strike in sorted(kalshi_strikes):
        if strike > trade_price:
            return strike
    return trade_price + 1.0


def get_trade_color(trade: TradeRecord, buy_color: str, sell_color: str) -> str:
    """Get color for trade based on side."""
    return buy_color if trade.trade_side == TradeSide.YES else sell_color


def get_strike_bounds(state, kalshi_strikes: List[float]) -> tuple[float, float]:
    """Get y_min and y_max from state or strikes."""
    if state.min_strike_price_cents is not None and state.max_strike_price_cents is not None:
        return state.min_strike_price_cents, state.max_strike_price_cents
    return min(kalshi_strikes), max(kalshi_strikes)


def apply_single_shading(
    ax,
    idx: int,
    y_min: float,
    y_max: float,
    color: str,
    alpha: float,
    time_window: TimeWindow = None,
) -> None:
    """Apply single shading to chart.

    When *time_window* ``(start, end)`` is provided the band is limited to
    that horizontal window via *xmin*/*xmax* in axes-relative coordinates.
    """
    import matplotlib.dates as mdates

    kwargs: dict = {"alpha": alpha, "color": color, "zorder": 5, "label": f"Trade {idx}"}

    if time_window is not None:
        start_time, end_time = time_window
        xlim = ax.get_xlim()
        x_range = float(xlim[1]) - float(xlim[0])
        if x_range > 0:
            start_num = mdates.date2num(start_time)
            end_num = mdates.date2num(end_time)
            kwargs["xmin"] = max(0.0, (start_num - float(xlim[0])) / x_range)
            kwargs["xmax"] = min(1.0, (end_num - float(xlim[0])) / x_range)

    ax.axhspan(y_min, y_max, **kwargs)
    logger.info("Applied shading %s: %s from %.0f°F to %.0f°F", idx, color, y_min, y_max)
