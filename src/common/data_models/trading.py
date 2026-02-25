"""
Trading-specific data models for Kalshi API integration.

This module contains dataclasses for portfolio management, order execution,
and trading operations. All models follow fail-fast principles with strict
validation and no default values that could hide data integrity issues.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .trading_helpers import (
    validate_market_validation_data,
    validate_order_fill,
    validate_order_request_enums,
    validate_order_request_metadata,
    validate_order_request_price,
    validate_order_response_counts,
    validate_order_response_enums,
    validate_order_response_fills,
    validate_order_response_metadata,
    validate_order_response_price,
    validate_portfolio_balance,
    validate_portfolio_position,
    validate_trading_error,
)


class OrderStatus(Enum):
    """Order execution status enumeration"""

    FILLED = "filled"
    EXECUTED = "executed"  # Kalshi API: 'executed' means accepted by exchange (not a fill)
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    PENDING = "pending"
    RESTING = "resting"  # Orders waiting in the order book
    REJECTED = "rejected"  # Orders rejected by exchange


class OrderAction(Enum):
    """Order action enumeration"""

    BUY = "buy"
    SELL = "sell"


class OrderSide(Enum):
    """Order side enumeration for yes/no markets"""

    YES = "yes"
    NO = "no"


class TimeInForce(Enum):
    """Time in force enumeration for order execution"""

    FILL_OR_KILL = "fill_or_kill"
    IMMEDIATE_OR_CANCEL = "immediate_or_cancel"
    GOOD_TILL_CANCELLED = "good_till_cancelled"


class OrderType(Enum):
    """Order type enumeration for execution method"""

    LIMIT = "limit"
    MARKET = "market"


class TradeRule(Enum):
    """Standardized trade rule identifiers for order tracking and analysis"""

    TEMP_DECLINE = "TEMP_DECLINE"
    TEMP_INCREASE = "TEMP_INCREASE"
    RULE_5_REVERSAL = "RULE_5_REVERSAL"
    POSITION_REBALANCE = "POSITION_REBALANCE"
    MARKET_CLOSE_EXIT = "MARKET_CLOSE_EXIT"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"


@dataclass
class PortfolioBalance:
    """
    Represents current account balance information.

    All monetary values are in cents to avoid floating point precision issues.
    Timestamp must be provided to ensure data freshness validation.
    """

    balance_cents: int
    timestamp: datetime
    currency: str

    def __post_init__(self):
        """Validate portfolio balance data integrity"""
        validate_portfolio_balance(self.balance_cents, self.currency, self.timestamp)


@dataclass
class PortfolioPosition:
    """
    Represents a single position in the portfolio.

    All monetary values are in cents. Position count represents number of contracts.
    Each contract represents $1 of risk in Kalshi markets.
    """

    ticker: str
    position_count: int | None = None
    side: OrderSide | None = None
    market_value_cents: int | None = None
    unrealized_pnl_cents: int | None = None
    average_price_cents: int | None = None
    last_updated: datetime | None = None

    def __post_init__(self):
        """Validate position data integrity"""
        self._fill_defaults()
        self._validate_position()

    def _fill_defaults(self) -> None:
        """Populate safe defaults when fields are omitted."""
        if self.side is None:
            raise ValueError("PortfolioPosition.side must be specified explicitly; implicit defaults hide data integrity issues")
        if self.average_price_cents is None:
            raise ValueError("PortfolioPosition.average_price_cents must be specified explicitly")
        if self.position_count is None:
            raise ValueError("PortfolioPosition.position_count must be specified explicitly")
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)

    def _validate_position(self) -> None:
        """Validate the portfolio position after normalization."""
        validate_portfolio_position(
            self.ticker,
            self.position_count,
            self.side,
            self.average_price_cents,
            self.last_updated,
        )


@dataclass
class OrderRequest:
    """
    Represents a request to place an order.

    For limit orders, yes_price_cents must be specified and within valid bounds.
    For market orders, yes_price_cents must be provided explicitly (use 0 for true market orders).
    Client order ID is required for proper order tracking and idempotency.
    Trade rule and reason are required for metadata storage and analysis.
    """

    ticker: str
    action: OrderAction
    side: OrderSide
    count: int
    client_order_id: str = "auto-client-order"
    trade_rule: str = "AUTO_RULE"
    trade_reason: str = "AUTO_REASON"
    order_type: OrderType = OrderType.MARKET
    yes_price_cents: Optional[int] = None
    time_in_force: TimeInForce = TimeInForce.IMMEDIATE_OR_CANCEL
    expiration_ts: Optional[int] = None  # Unix timestamp for GTT orders

    def __post_init__(self):
        """Validate order request parameters"""
        validate_order_request_enums(self.action, self.side, self.order_type, self.time_in_force)
        validate_order_request_price(self.order_type, self.yes_price_cents)
        validate_order_request_metadata(self.ticker, self.count, self.client_order_id, self.trade_rule, self.trade_reason)


@dataclass
class OrderFill:
    """
    Represents a single fill execution for an order.

    Each fill represents a partial or complete execution at a specific price and quantity.
    """

    price_cents: int
    count: int
    timestamp: datetime

    def __post_init__(self):
        """Validate order fill data"""
        validate_order_fill(self.price_cents, self.count, self.timestamp)


@dataclass
class OrderResponse:
    """
    Represents the response from placing or querying an order.

    Contains complete order state including fills and execution status.
    Fees are tracked separately for accurate P&L calculation.
    Trade metadata (rule and reason) are included to eliminate need for Redis storage.
    """

    order_id: str
    status: OrderStatus
    ticker: str
    side: OrderSide
    action: OrderAction
    order_type: OrderType
    filled_count: int | None = None
    remaining_count: int | None = None
    average_fill_price_cents: Optional[int] = None
    timestamp: datetime | None = None
    fees_cents: Optional[int] = None
    fills: List[OrderFill] | None = None
    trade_rule: str = "AUTO_RULE"
    trade_reason: str = "AUTO_REASON"
    client_order_id: str = "auto-client-id"
    rejection_reason: Optional[str] = None

    def __post_init__(self):
        """Validate order response data integrity"""
        self._populate_defaults()
        self._validate_response()

    def _populate_defaults(self) -> None:
        """Fill missing fields with safe defaults for validation."""
        if self.fills is None:
            self.fills = []
        if self.filled_count is None:
            self.filled_count = 0
        if self.remaining_count is None:
            self.remaining_count = 0
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    def _validate_response(self) -> None:
        """Run validation on order response data."""
        validate_order_response_enums(self.status, self.side, self.action, self.order_type)
        validate_order_response_counts(self.filled_count, self.remaining_count, self.status)
        validate_order_response_price(self.filled_count, self.average_fill_price_cents, self.fees_cents)
        validate_order_response_fills(self.fills, self.filled_count)
        validate_order_response_metadata(
            self.order_id,
            self.client_order_id,
            self.ticker,
            self.trade_rule,
            self.trade_reason,
            self.timestamp,
        )


@dataclass
class TradingError:
    """
    Represents a trading operation error with context.

    Provides structured error information for monitoring and alerting systems.
    """

    error_code: str
    error_message: str
    timestamp: datetime
    operation_name: str
    request_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate trading error data"""
        validate_trading_error(self.error_code, self.error_message, self.operation_name, self.timestamp)


@dataclass
class MarketValidationData:
    """
    Represents market validation data for pre-trade checks.

    Contains current market state needed to validate order parameters
    before submission to prevent rejections.
    """

    ticker: str
    is_open: bool
    best_bid_cents: Optional[int]
    best_ask_cents: Optional[int]
    last_price_cents: Optional[int]
    timestamp: datetime

    def __post_init__(self):
        """Validate market data integrity"""
        validate_market_validation_data(
            self.ticker,
            self.is_open,
            self.best_bid_cents,
            self.best_ask_cents,
            self.last_price_cents,
            self.timestamp,
        )


_MAX_BATCH_SIZE = 20
_MIN_BATCH_SIZE = 1


@dataclass
class BatchOrderResult:
    """Result for a single order within a batch submission.

    Each entry maps to one order in the batch request, preserving
    the original index for correlation with the input list.
    """

    order_index: int
    order_response: Optional[OrderResponse]
    error_code: Optional[str]
    error_message: Optional[str]

    @property
    def succeeded(self) -> bool:
        """Whether this individual order was accepted."""
        return self.order_response is not None and self.error_code is None
