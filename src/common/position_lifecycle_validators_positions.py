"""
Position Lifecycle Validators for Kalshi Live Trading Tests

This module provides core snapshot dataclasses and position-level transition
validation helpers. Portfolio-wide checks live in the companion module
`position_lifecycle_validators_portfolio`.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from common.truthy import pick_if, pick_truthy

from .data_models.trading import (
    OrderResponse,
    OrderSide,
    PortfolioBalance,
    PortfolioPosition,
)

logger = logging.getLogger(__name__)


# Constants
_CONST_100 = 100


@dataclass
class PositionStateSnapshot:
    """Snapshot of position state at a specific point in time"""

    ticker: str
    position_count: int
    side: OrderSide
    market_value_cents: int
    unrealized_pnl_cents: int
    average_price_cents: int
    timestamp: datetime

    def __post_init__(self):
        if not self.ticker:
            raise ValueError("Ticker cannot be empty")


@dataclass
class BalanceStateSnapshot:
    """Snapshot of portfolio balance at a specific point in time"""

    balance_cents: int
    timestamp: datetime


@dataclass
class TradeExecution:
    """Record of a completed trade execution"""

    order_id: str
    ticker: str
    side: OrderSide
    action: str  # "BUY" or "SELL"
    filled_count: int
    average_fill_price_cents: int
    fees_cents: int
    timestamp: datetime

    def __post_init__(self):
        if not self.order_id:
            raise ValueError("Order ID cannot be empty")
        if not self.ticker:
            raise ValueError("Ticker cannot be empty")
        if self.filled_count <= 0:
            raise TypeError(f"Filled count must be positive: {self.filled_count}")
        if self.average_fill_price_cents <= 0 or self.average_fill_price_cents > _CONST_100:
            raise TypeError(f"Fill price must be 1-100 cents: {self.average_fill_price_cents}")
        if self.fees_cents < 0:
            raise ValueError(f"Fees cannot be negative: {self.fees_cents}")


def validate_position_state_transition(
    before: Optional[PositionStateSnapshot], after: PositionStateSnapshot, trade: TradeExecution
) -> Tuple[bool, str]:
    """
    Validate that position state transition matches the executed trade.

    Args:
        before: Position state before trade (None if no position existed)
        after: Position state after trade
        trade: The executed trade that should cause the transition

    Returns:
        Tuple of (is_valid, error_message)

    Raises:
        ArithmeticError: If arithmetic operation fails during validation
        AttributeError: If required attribute is missing
        TypeError: If type mismatch occurs during validation
        ValueError: If value is invalid during validation
    """
    # Validate basic fields match
    is_valid, error = _validate_basic_fields(after, trade)
    if not is_valid:
        return False, error

    # Calculate expected position count change
    expected_count_change = _calculate_expected_count_change(trade)
    if expected_count_change is None:
        _none_guard_value = False, f"Invalid trade action: {trade.action}"
        return _none_guard_value

    # Validate position count
    is_valid, error = _validate_position_count(before, after, expected_count_change)
    if not is_valid:
        return False, error

    # Validate average price for BUY orders
    if trade.action == "BUY" and after.position_count > 0:
        is_valid, error = _validate_average_price(before, after, trade)
        if not is_valid:
            return False, error

    return True, "Position state transition valid"


def _validate_basic_fields(after: PositionStateSnapshot, trade: TradeExecution) -> Tuple[bool, str]:
    """Validate ticker and side match between position and trade."""
    if after.ticker != trade.ticker:
        return False, f"Ticker mismatch: position={after.ticker}, trade={trade.ticker}"

    if after.side != trade.side:
        return False, f"Side mismatch: position={after.side.value}, trade={trade.side.value}"

    return True, ""


def _calculate_expected_count_change(trade: TradeExecution) -> Optional[int]:
    """Calculate expected position count change from trade action."""
    if trade.action == "BUY":
        return trade.filled_count
    if trade.action == "SELL":
        return -trade.filled_count
    return None


def _validate_position_count(
    before: Optional[PositionStateSnapshot], after: PositionStateSnapshot, expected_change: int
) -> Tuple[bool, str]:
    """Validate position count changed correctly."""
    before_count = int() if before is None else before.position_count
    expected_after_count = before_count + expected_change

    if after.position_count != expected_after_count:
        return False, (
            f"Position count mismatch: expected={expected_after_count}, "
            f"actual={after.position_count} (before={before_count}, change={expected_change})"
        )

    return True, ""


def _validate_average_price(
    before: Optional[PositionStateSnapshot],
    after: PositionStateSnapshot,
    trade: TradeExecution,
) -> Tuple[bool, str]:
    """Validate average price calculation for BUY orders."""
    if before and before.position_count > 0:
        # Weighted average calculation
        total_cost = before.position_count * before.average_price_cents + trade.filled_count * trade.average_fill_price_cents
        expected_avg_price = total_cost // after.position_count

        # Allow 1 cent tolerance for rounding
        if abs(after.average_price_cents - expected_avg_price) > 1:
            return False, (f"Average price calculation error: expected≈{expected_avg_price}¢, " f"actual={after.average_price_cents}¢")
    # First position - average price should equal fill price
    elif after.average_price_cents != trade.average_fill_price_cents:
        return False, (
            f"First position average price mismatch: expected={trade.average_fill_price_cents}¢, " f"actual={after.average_price_cents}¢"
        )

    return True, ""


def create_position_snapshot(position: PortfolioPosition) -> PositionStateSnapshot:
    """Create a position state snapshot from a PortfolioPosition"""
    position_count = position.position_count
    if position_count is None:
        raise ValueError("Cannot build snapshot with incomplete position data")
    side = position.side
    if side is None:
        raise ValueError("Cannot build snapshot with incomplete position data")
    market_value = position.market_value_cents
    if market_value is None:
        raise ValueError("Cannot build snapshot with incomplete position data")
    unrealized_pnl = position.unrealized_pnl_cents
    if unrealized_pnl is None:
        raise ValueError("Cannot build snapshot with incomplete position data")
    average_price = position.average_price_cents
    if average_price is None:
        raise ValueError("Cannot build snapshot with incomplete position data")
    timestamp = position.last_updated
    if timestamp is None:
        raise ValueError("Cannot build snapshot with incomplete position data")
    return PositionStateSnapshot(
        ticker=position.ticker,
        position_count=position_count,
        side=side,
        market_value_cents=market_value,
        unrealized_pnl_cents=unrealized_pnl,
        average_price_cents=average_price,
        timestamp=timestamp,
    )


def create_balance_snapshot(balance: PortfolioBalance) -> BalanceStateSnapshot:
    """Create a balance state snapshot from a PortfolioBalance"""
    return BalanceStateSnapshot(balance_cents=balance.balance_cents, timestamp=balance.timestamp)


def create_trade_execution(order_response: OrderResponse, ticker: str, side: OrderSide, action: str) -> TradeExecution:
    """Create a trade execution record from an OrderResponse"""
    avg_price = order_response.average_fill_price_cents
    if avg_price is None:
        raise ValueError(f"Order response for {order_response.order_id} missing average fill price; cannot create trade execution")
    filled_count = order_response.filled_count
    if filled_count is None:
        raise ValueError("Order response missing filled count; cannot build trade execution")
    timestamp = order_response.timestamp
    if timestamp is None:
        raise ValueError("Order response missing timestamp; cannot build trade execution")
    fees_cents = order_response.fees_cents
    if fees_cents is None:
        fees_cents = int()
    return TradeExecution(
        order_id=order_response.order_id,
        ticker=ticker,
        side=side,
        action=action,
        filled_count=filled_count,
        average_fill_price_cents=avg_price,
        fees_cents=fees_cents,
        timestamp=timestamp,
    )


__all__ = [
    "BalanceStateSnapshot",
    "PositionStateSnapshot",
    "TradeExecution",
    "create_balance_snapshot",
    "create_position_snapshot",
    "create_trade_execution",
    "validate_position_state_transition",
]
