"""Portfolio-level validators split from the position module."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from src.common.data_models.trading import (
    OrderAction,
    OrderResponse,
    OrderSide,
    PortfolioPosition,
)

from .position_lifecycle_validators_positions import (
    BalanceStateSnapshot,
    TradeExecution,
)

# Constants
_CONST_10 = 10
_CONST_100 = 100


def validate_portfolio_balance_arithmetic(
    before: BalanceStateSnapshot, after: BalanceStateSnapshot, trades: List[TradeExecution]
) -> Tuple[bool, str]:
    """
    Validate portfolio balance changes match executed trades.

    Args:
        before: Balance before trades
        after: Balance after trades
        trades: List of executed trades

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Calculate expected balance change
        total_cost = 0
        total_proceeds = 0
        total_fees = 0

        for trade in trades:
            trade_value = trade.filled_count * trade.average_fill_price_cents
            total_fees += trade.fees_cents

            if trade.action == "BUY":
                total_cost += trade_value
            elif trade.action == "SELL":
                total_proceeds += trade_value
            else:
                return False, f"Invalid trade action: {trade.action}"

        # Expected balance change = proceeds - cost - fees
        expected_balance_change = total_proceeds - total_cost - total_fees
        actual_balance_change = after.balance_cents - before.balance_cents

        if actual_balance_change != expected_balance_change:
            return False, (
                f"Balance arithmetic mismatch: expected_change={expected_balance_change}¢, "
                f"actual_change={actual_balance_change}¢ "
                f"(cost={total_cost}¢, proceeds={total_proceeds}¢, fees={total_fees}¢)"
            )

        else:
            return True, "Portfolio balance arithmetic valid"
    except (
        ArithmeticError,
        AttributeError,
        TypeError,
        ValueError,
    ):
        return False, f"Balance validation error"


def validate_position_pnl_consistency(position: PortfolioPosition) -> Tuple[bool, str]:
    """
    Validate internal P&L arithmetic consistency within a position.

    Market value should equal cost basis plus unrealized P&L.

    Args:
        position: Position to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        position_count = position.position_count
        average_price = position.average_price_cents
        market_value = position.market_value_cents
        unrealized_pnl = position.unrealized_pnl_cents

        if (
            position_count is None
            or average_price is None
            or market_value is None
            or unrealized_pnl is None
        ):
            return False, "Incomplete position data for P&L validation"

        # Calculate cost basis
        cost_basis_cents = position_count * average_price

        # Market value should equal cost basis + unrealized P&L
        expected_market_value = cost_basis_cents + unrealized_pnl

        if market_value != expected_market_value:
            return False, (
                f"P&L arithmetic inconsistent: market_value={market_value}¢, "
                f"expected={expected_market_value}¢ "
                f"(cost_basis={cost_basis_cents}¢, unrealized_pnl={unrealized_pnl}¢)"
            )
    except (
        ArithmeticError,
        AttributeError,
        TypeError,
        ValueError,
    ):
        return False, f"P&L validation error"
    else:
        return True, "Position P&L arithmetic consistent"


def validate_position_exposure_limits(
    position: PortfolioPosition, max_exposure_cents: int
) -> Tuple[bool, str]:
    """
    Validate position exposure is within risk limits.

    Args:
        position: Position to validate
        max_exposure_cents: Maximum allowed exposure in cents

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        market_value = position.market_value_cents
        if market_value is None:
            return False, "Position missing market value for exposure check"
        # Calculate current exposure (market value represents current risk)
        current_exposure = abs(market_value)

        if current_exposure > max_exposure_cents:
            return False, (
                f"Position exposure exceeds limit: current={current_exposure}¢, "
                f"limit={max_exposure_cents}¢"
            )

        else:
            return True, "Position exposure within limits"
    except (
        ArithmeticError,
        AttributeError,
        TypeError,
        ValueError,
    ):
        return False, f"Exposure validation error"


def validate_trade_execution_consistency(
    order_response: OrderResponse,
    expected_ticker: str,
    expected_side: OrderSide,
    expected_action: str,
) -> Tuple[bool, str]:
    """
    Validate trade execution matches order parameters.

    Args:
        order_response: Response from order execution
        expected_ticker: Expected ticker symbol
        expected_side: Expected order side (YES/NO)
        expected_action: Expected action (BUY/SELL)

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Validate order metadata
        is_valid, error = _validate_order_metadata(
            order_response, expected_ticker, expected_side, expected_action
        )
        if not is_valid:
            return False, error

        # Validate execution details
        is_valid, error = _validate_execution_details(order_response)
        if not is_valid:
            return False, error

        # Validate fees
        is_valid, error = _validate_execution_fees(order_response)
        if not is_valid:
            return False, error

        else:
            return True, "Trade execution consistent"
    except (
        ArithmeticError,
        AttributeError,
        TypeError,
        ValueError,
        ZeroDivisionError,
    ):
        return False, f"Execution validation error"


def _validate_ticker_field(actual_ticker: str | None, expected_ticker: str) -> Tuple[bool, str]:
    """Validate ticker field matches expectation."""
    if not actual_ticker:
        return False, "Order response missing ticker"
    if actual_ticker != expected_ticker:
        return False, f"Ticker mismatch: expected {expected_ticker}, got {actual_ticker}"
    return True, ""


def _validate_side_field(
    actual_side: OrderSide | None, expected_side: OrderSide
) -> Tuple[bool, str]:
    """Validate side field matches expectation."""
    if not isinstance(actual_side, OrderSide):
        return False, f"Order response missing valid side attribute (got {actual_side})"
    if actual_side != expected_side:
        return False, f"Side mismatch: expected {expected_side}, got {actual_side}"
    return True, ""


def _validate_action_field(actual_action: Any, expected_action: str) -> Tuple[bool, str]:
    """Validate action field matches expectation."""
    actual_action_value = _extract_action_value(actual_action)
    if actual_action_value is None:
        return False, "Order response missing action attribute"

    expected_action_upper = expected_action.upper()
    if actual_action_value.upper() != expected_action_upper:
        return (
            False,
            f"Action mismatch: expected {expected_action_upper}, got {actual_action_value}",
        )
    return True, ""


def _validate_order_metadata(
    order_response: OrderResponse,
    expected_ticker: str,
    expected_side: OrderSide,
    expected_action: str,
) -> Tuple[bool, str]:
    """Validate order metadata matches expectations."""
    actual_ticker = getattr(order_response, "ticker", None)
    is_valid, error = _validate_ticker_field(actual_ticker, expected_ticker)
    if not is_valid:
        return False, error

    actual_side = getattr(order_response, "side", None)
    is_valid, error = _validate_side_field(actual_side, expected_side)
    if not is_valid:
        return False, error

    actual_action = getattr(order_response, "action", None)
    return _validate_action_field(actual_action, expected_action)


def _extract_action_value(actual_action: Any) -> Optional[str]:
    """Extract action value from OrderAction enum or string."""
    if isinstance(actual_action, OrderAction):
        return actual_action.value
    if actual_action is not None:
        return str(actual_action)
    return None


def _validate_execution_details(order_response: OrderResponse) -> Tuple[bool, str]:
    """Validate basic execution details."""
    # Validate filled count
    filled_count = order_response.filled_count
    if filled_count is None:
        return False, "Order response missing filled_count"
    if filled_count <= 0:
        return False, f"No execution: filled_count={filled_count}"

    # Validate price bounds
    avg_price = order_response.average_fill_price_cents
    if avg_price is None:
        return False, "Missing average fill price in order response"
    if avg_price <= 0 or avg_price > _CONST_100:
        return False, f"Invalid fill price: {avg_price}¢ (must be 1-100¢)"

    return True, ""


def _validate_execution_fees(order_response: OrderResponse) -> Tuple[bool, str]:
    """Validate fees are reasonable."""
    avg_price = order_response.average_fill_price_cents
    if avg_price is None:
        return True, ""  # Already validated in execution details

    filled_count = order_response.filled_count
    if filled_count is None:
        return True, ""  # Guard against missing filled count
    trade_value = filled_count * avg_price
    fees_cents = order_response.fees_cents or 0

    if trade_value <= 0:
        return True, ""  # Skip fee validation for zero-value trades

    fee_percentage = (fees_cents / trade_value) * 100

    # Fees shouldn't exceed 10% of trade value
    if fee_percentage > _CONST_10:
        return False, (
            f"Excessive fees: {fees_cents}¢ ({fee_percentage:.1f}%) "
            f"on trade value {trade_value}¢"
        )

    return True, ""


__all__ = [
    "validate_portfolio_balance_arithmetic",
    "validate_position_pnl_consistency",
    "validate_position_exposure_limits",
    "validate_trade_execution_consistency",
]
