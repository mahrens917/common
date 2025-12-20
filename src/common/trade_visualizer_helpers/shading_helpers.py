from __future__ import annotations

"""Helper functions for ShadingBuilder."""


import logging
from typing import TYPE_CHECKING, List

from common.data_models.trade_record import TradeRecord, TradeSide

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


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


def apply_single_shading(ax, idx: int, y_min: float, y_max: float, color: str, alpha: float) -> None:
    """Apply single shading to chart."""
    ax.axhspan(y_min, y_max, alpha=alpha, color=color, zorder=5, label=f"Trade {idx}")
    logger.info("Applied shading %s: %s from %.0f°F to %.0f°F", idx, color, y_min, y_max)
