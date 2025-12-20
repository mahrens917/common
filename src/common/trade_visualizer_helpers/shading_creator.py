"""Shading creation helpers for trade visualizer."""

from datetime import datetime
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .shading_builder import ShadingBuilder, TradeShading


def create_executed_trade_shading(
    shading_builder: "ShadingBuilder",
    trade,
    kalshi_strikes: List[float],
    temperature_timestamps: List[datetime],
) -> "TradeShading | None":
    """Create shading for executed trade."""
    return shading_builder.create_executed_trade_shading(trade, kalshi_strikes, temperature_timestamps)


def create_no_liquidity_shading(
    shading_builder: "ShadingBuilder",
    state,
    kalshi_strikes: List[float],
    temperature_timestamps: List[datetime],
) -> "TradeShading | None":
    """Create no-liquidity shading."""
    return shading_builder.create_no_liquidity_shading(state, kalshi_strikes, temperature_timestamps)


def is_no_liquidity_state(shading_builder: "ShadingBuilder", state) -> bool:
    """Check if state represents no liquidity."""
    return shading_builder.is_no_liquidity_state(state)


def safe_float(liquidity_fetcher, value):
    """Safe float conversion."""
    return liquidity_fetcher.safe_float(value)
