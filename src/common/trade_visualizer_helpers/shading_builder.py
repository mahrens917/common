from __future__ import annotations

"""Build shading regions for trade visualization."""


import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from matplotlib.axes import Axes

from common.constants.trading import MAX_MARKET_PRICE_CENTS, MIN_MARKET_PRICE_CENTS
from common.data_models.trade_record import TradeRecord
from common.trade_visualizer_helpers import shading_helpers

logger = logging.getLogger(__name__)


@dataclass
class TradeShading:
    """Lightweight container describing a shaded band for the temperature chart."""

    start_time: datetime
    end_time: datetime
    y_min: float
    y_max: float
    color: str
    alpha: float
    label: str


class ShadingBuilder:
    """Build shading regions for trades and liquidity."""

    EXECUTED_BUY_COLOR = "#90EE90"
    EXECUTED_SELL_COLOR = "#FFB6C1"
    UNEXECUTED_COLOR = "#808080"
    DEFAULT_ALPHA = 0.3

    @staticmethod
    def is_no_liquidity_state(state) -> bool:
        """Check if state represents no liquidity."""
        bid = state.yes_bid
        ask = state.yes_ask
        return (bid is None or bid == MIN_MARKET_PRICE_CENTS) and (ask is None or ask == MAX_MARKET_PRICE_CENTS)

    def create_executed_trade_shading(
        self,
        trade: TradeRecord,
        kalshi_strikes: List[float],
        temperature_timestamps: List[datetime],
    ) -> Optional[TradeShading]:
        """Create shading for an executed trade."""
        try:
            trade_price = float(trade.price_cents)
            next_strike = shading_helpers.find_next_strike(trade_price, kalshi_strikes)
            color = shading_helpers.get_trade_color(trade, self.EXECUTED_BUY_COLOR, self.EXECUTED_SELL_COLOR)
            window = timedelta(minutes=30)
            return TradeShading(
                start_time=trade.trade_timestamp - window,
                end_time=trade.trade_timestamp + window,
                y_min=trade_price,
                y_max=next_strike,
                color=color,
                alpha=self.DEFAULT_ALPHA,
                label=f"Executed {trade.trade_side.value} at {trade_price:.0f}°F",
            )
        except (ValueError, AttributeError, TypeError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            # pragma: no cover - defensive logging
            logger.exception("Failed to create executed trade shading")
            return None

    def create_no_liquidity_shading(
        self,
        state,
        kalshi_strikes: List[float],
        temperature_timestamps: List[datetime],
    ) -> Optional[TradeShading]:
        """Create shading for no liquidity state."""
        try:
            if not kalshi_strikes:
                return None
            y_min, y_max = shading_helpers.get_strike_bounds(state, kalshi_strikes)
            window = timedelta(hours=1)
            return TradeShading(
                start_time=state.timestamp - window,
                end_time=state.timestamp + window,
                y_min=y_min,
                y_max=y_max,
                color=self.UNEXECUTED_COLOR,
                alpha=self.DEFAULT_ALPHA,
                label=f"No liquidity in {state.market_ticker}",
            )
        except (ValueError, AttributeError, TypeError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            # pragma: no cover - defensive logging
            logger.exception("Failed to create no-liquidity shading")
            return None

    @staticmethod
    def apply_trade_shadings_to_chart(
        ax: Axes,
        shadings: List[TradeShading],
        timestamps_for_chart: List[datetime],
    ) -> None:
        """Apply shadings to a matplotlib chart."""
        try:
            logger.info(
                "Applying %s trade shadings to chart across %s timestamps",
                len(shadings),
                len(timestamps_for_chart),
            )
            for idx, shading in enumerate(shadings, start=1):
                shading_helpers.apply_single_shading(
                    ax,
                    idx,
                    shading.y_min,
                    shading.y_max,
                    shading.color,
                    shading.alpha,
                    time_window=(shading.start_time, shading.end_time),
                )
        except (
            ValueError,
            RuntimeError,
            AttributeError,
        ):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            # pragma: no cover - defensive logging
            logger.exception("Failed to apply trade shadings to chart")
