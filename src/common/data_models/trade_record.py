"""Trade record data models for Kalshi trading report system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

from common.validation_guards import (
    require,
    require_date,
    require_non_negative,
    require_percentage,
)

from .trade_record_helpers import (
    calculate_current_pnl_cents,
    calculate_realised_pnl_cents,
    get_current_market_price_cents,
    get_trade_close_date,
)
from .trade_record_helpers import is_trade_reason_valid as is_trade_reason_valid
from .trade_record_helpers import (
    validate_trade_record,
)

__all__ = [
    "TradeSide",
    "TradeRecord",
    "calculate_current_pnl_cents",
    "calculate_realised_pnl_cents",
    "get_current_market_price_cents",
    "get_trade_close_date",
    "is_trade_reason_valid",
    "validate_trade_record",
]


class TradeSide(Enum):
    """Trade side enumeration for yes/no markets"""

    YES = "yes"
    NO = "no"


@dataclass
class TradeRecord:
    """
    Represents a single trade record with current market value for P&L calculation.

    All monetary values are in cents to avoid floating point precision issues.
    Trade reasons and rules are retrieved from Redis storage for rule-based analysis.
    """

    order_id: str
    market_ticker: str
    trade_timestamp: datetime  # Single source of truth for time data
    trade_side: TradeSide
    quantity: int
    price_cents: int
    fee_cents: int  # Fees charged by Kalshi (from maker_fees field)
    cost_cents: int  # Total cost including fees: (price_cents * quantity) + fee_cents
    market_category: str  # Lowercase Kalshi category (for example "weather", "binary")
    trade_rule: str  # Must be retrieved from Redis when order is placed
    trade_reason: str  # Must be retrieved from Redis when order is placed
    weather_station: Optional[str] = None  # Required for weather trades; optional otherwise

    # Latest market prices in cents (updated in real-time for P&L calculations)
    last_yes_bid: Optional[int] = None
    last_yes_ask: Optional[int] = None
    last_price_update: Optional[datetime] = None

    # Settlement information (populated once Kalshi declares a result)
    settlement_price_cents: Optional[int] = None
    settlement_time: Optional[datetime] = None

    def __post_init__(self):
        """Validate trade record data integrity"""
        validate_trade_record(self)

    def realised_pnl_cents(self) -> Optional[int]:
        """Return realised P&L if the market has settled."""
        return calculate_realised_pnl_cents(
            self.settlement_price_cents,
            self.trade_side,
            self.quantity,
            self.cost_cents,
        )

    def _current_market_price_cents(self) -> Optional[int]:
        return get_current_market_price_cents(
            self.trade_side,
            self.last_yes_bid,
            self.last_yes_ask,
        )

    def calculate_current_pnl_cents(self) -> int:
        """Calculate current or realised P&L in cents."""
        return calculate_current_pnl_cents(self)

    @property
    def is_settled(self) -> bool:
        return self.settlement_price_cents is not None


@dataclass
class PnLBreakdown:
    """
    Represents profit/loss breakdown for a specific category.

    Used for aggregating P&L by weather station, hour, or trading rule.
    """

    trades_count: int
    cost_cents: int
    pnl_cents: int
    win_rate: float

    def __post_init__(self):
        """Validate P&L breakdown data"""
        if self.trades_count < 0:
            raise ValueError(f"Trades count cannot be negative: {self.trades_count}")

        if self.cost_cents < 0:
            raise ValueError(f"Cost cannot be negative: {self.cost_cents}")

        if self.win_rate < 0.0 or self.win_rate > 1.0:
            raise TypeError(f"Win rate must be between 0.0 and 1.0: {self.win_rate}")


@dataclass
class PnLReport:
    """
    Represents a comprehensive profit/loss report for a specific date range.

    Contains total metrics and detailed breakdowns by various categories.
    """

    report_date: date
    start_date: date
    end_date: date
    total_trades: int
    total_cost_cents: int
    total_pnl_cents: int
    win_rate: float

    # Detailed breakdowns
    by_weather_station: dict[str, PnLBreakdown]
    by_rule: dict[str, PnLBreakdown]

    def __post_init__(self):
        """Validate P&L report data integrity"""
        self._validate_date_range()
        self._validate_totals()

    def _validate_date_range(self) -> None:
        """Ensure report range inputs are valid dates in chronological order."""
        require_date(self.report_date, "Report date")
        require_date(self.start_date, "Start date")
        require_date(self.end_date, "End date")
        require(
            self.start_date <= self.end_date,
            ValueError("Start date cannot be after end date"),
        )

    def _validate_totals(self) -> None:
        """Validate total metrics."""
        require_non_negative(self.total_trades, "Total trades")
        require_non_negative(self.total_cost_cents, "Total cost")
        require_percentage(self.win_rate, "Win rate")


__all__ = [
    "TradeRecord",
    "TradeSide",
    "PnLBreakdown",
    "PnLReport",
    "get_trade_close_date",
]
