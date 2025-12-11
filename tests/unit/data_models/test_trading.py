"""Unit tests for common data_models trading module."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from common.data_models.trading import (
    MarketValidationData,
    OrderAction,
    OrderFill,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    PortfolioBalance,
    PortfolioPosition,
    TimeInForce,
    TradeRule,
    TradingError,
)

DEFAULT_FILL_PRICE = 75
DEFAULT_FILLED_COUNT = 10
DEFAULT_REMAINING_COUNT = 0
DEFAULT_FEES = 2
REJECTED_ORDER_REMAINING_COUNT = 10
ZERO_FILLED_COUNT = 0


class TestEnums:
    """Tests for trading enum types."""

    def test_order_status_values(self):
        """Test OrderStatus enum has all expected values."""
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.EXECUTED.value == "executed"
        assert OrderStatus.PARTIALLY_FILLED.value == "partially_filled"
        assert OrderStatus.CANCELLED.value == "cancelled"
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.RESTING.value == "resting"
        assert OrderStatus.REJECTED.value == "rejected"

    def test_order_action_values(self):
        """Test OrderAction enum has all expected values."""
        assert OrderAction.BUY.value == "buy"
        assert OrderAction.SELL.value == "sell"

    def test_order_side_values(self):
        """Test OrderSide enum has all expected values."""
        assert OrderSide.YES.value == "yes"
        assert OrderSide.NO.value == "no"

    def test_time_in_force_values(self):
        """Test TimeInForce enum has all expected values."""
        assert TimeInForce.FILL_OR_KILL.value == "fill_or_kill"
        assert TimeInForce.IMMEDIATE_OR_CANCEL.value == "immediate_or_cancel"
        assert TimeInForce.GOOD_TILL_CANCELLED.value == "good_till_cancelled"

    def test_order_type_values(self):
        """Test OrderType enum has all expected values."""
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.MARKET.value == "market"

    def test_trade_rule_values(self):
        """Test TradeRule enum has all expected values."""
        assert TradeRule.TEMP_DECLINE.value == "TEMP_DECLINE"
        assert TradeRule.TEMP_INCREASE.value == "TEMP_INCREASE"
        assert TradeRule.RULE_5_REVERSAL.value == "RULE_5_REVERSAL"
        assert TradeRule.POSITION_REBALANCE.value == "POSITION_REBALANCE"
        assert TradeRule.MARKET_CLOSE_EXIT.value == "MARKET_CLOSE_EXIT"
        assert TradeRule.EMERGENCY_EXIT.value == "EMERGENCY_EXIT"


class TestPortfolioBalance:
    """Tests for PortfolioBalance dataclass."""

    def test_valid_creation(self):
        """Test creating PortfolioBalance with valid data."""
        now = datetime.now(timezone.utc)
        balance = PortfolioBalance(balance_cents=50000, timestamp=now, currency="USD")

        assert balance.balance_cents == 50000
        assert balance.timestamp == now
        assert balance.currency == "USD"

    def test_validation_called_on_init(self):
        """Test that validation is called during initialization."""
        now = datetime.now(timezone.utc)
        with patch("common.data_models.trading.validate_portfolio_balance") as mock_validate:
            PortfolioBalance(balance_cents=50000, timestamp=now, currency="USD")

            mock_validate.assert_called_once_with(50000, "USD", now)


class TestPortfolioPosition:
    """Tests for PortfolioPosition dataclass."""

    def test_valid_creation(self):
        """Test creating PortfolioPosition with valid data."""
        now = datetime.now(timezone.utc)
        position = PortfolioPosition(
            ticker="KMARKT-25JAN01",
            position_count=100,
            side=OrderSide.YES,
            market_value_cents=7500,
            unrealized_pnl_cents=500,
            average_price_cents=70,
            last_updated=now,
        )

        assert position.ticker == "KMARKT-25JAN01"
        assert position.position_count == 100
        assert position.side == OrderSide.YES
        assert position.market_value_cents == 7500
        assert position.unrealized_pnl_cents == 500
        assert position.average_price_cents == 70
        assert position.last_updated == now

    def test_validation_called_on_init(self):
        """Test that validation is called during initialization."""
        now = datetime.now(timezone.utc)
        with patch("common.data_models.trading.validate_portfolio_position") as mock_validate:
            PortfolioPosition(
                ticker="KMARKT-25JAN01",
                position_count=100,
                side=OrderSide.YES,
                market_value_cents=7500,
                unrealized_pnl_cents=500,
                average_price_cents=70,
                last_updated=now,
            )

            mock_validate.assert_called_once_with("KMARKT-25JAN01", 100, OrderSide.YES, 70, now)


class TestOrderRequest:
    """Tests for OrderRequest dataclass."""

    def test_valid_creation_market_order(self):
        """Test creating OrderRequest for market order."""
        request = OrderRequest(
            ticker="KMARKT-25JAN01",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            count=10,
            client_order_id="order-123",
            trade_rule="TEMP_INCREASE",
            trade_reason="Temperature rising above threshold",
            yes_price_cents=0,  # Market orders must specify price (0 for exchange default)
        )

        assert request.ticker == "KMARKT-25JAN01"
        assert request.action == OrderAction.BUY
        assert request.side == OrderSide.YES
        assert request.count == 10
        assert request.client_order_id == "order-123"
        assert request.trade_rule == "TEMP_INCREASE"
        assert request.trade_reason == "Temperature rising above threshold"
        assert request.order_type == OrderType.MARKET
        assert request.time_in_force == TimeInForce.IMMEDIATE_OR_CANCEL
        assert request.yes_price_cents == 0
        assert request.expiration_ts is None

    def test_valid_creation_limit_order(self):
        """Test creating OrderRequest for limit order."""
        request = OrderRequest(
            ticker="KMARKT-25JAN01",
            action=OrderAction.BUY,
            side=OrderSide.YES,
            count=10,
            client_order_id="order-123",
            trade_rule="TEMP_INCREASE",
            trade_reason="Temperature rising",
            order_type=OrderType.LIMIT,
            yes_price_cents=75,
        )

        assert request.order_type == OrderType.LIMIT
        assert request.yes_price_cents == 75

    def test_validation_called_on_init(self):
        """Test that all validation functions are called."""
        with patch("common.data_models.trading.validate_order_request_enums") as mock_enum_val:
            with patch("common.data_models.trading.validate_order_request_price") as mock_price_val:
                with patch("common.data_models.trading.validate_order_request_metadata") as mock_meta_val:
                    request = OrderRequest(
                        ticker="KMARKT-25JAN01",
                        action=OrderAction.BUY,
                        side=OrderSide.YES,
                        count=10,
                        client_order_id="order-123",
                        trade_rule="TEMP_INCREASE",
                        trade_reason="Temperature rising",
                        yes_price_cents=0,
                    )

                    mock_enum_val.assert_called_once_with(
                        OrderAction.BUY,
                        OrderSide.YES,
                        OrderType.MARKET,
                        TimeInForce.IMMEDIATE_OR_CANCEL,
                    )
                    mock_price_val.assert_called_once_with(OrderType.MARKET, 0)
                    mock_meta_val.assert_called_once_with("KMARKT-25JAN01", 10, "order-123", "TEMP_INCREASE", "Temperature rising")


class TestOrderFill:
    """Tests for OrderFill dataclass."""

    def test_valid_creation(self):
        """Test creating OrderFill with valid data."""
        now = datetime.now(timezone.utc)
        fill = OrderFill(price_cents=75, count=10, timestamp=now)

        assert fill.price_cents == 75
        assert fill.count == 10
        assert fill.timestamp == now

    def test_validation_called_on_init(self):
        """Test that validation is called during initialization."""
        now = datetime.now(timezone.utc)
        with patch("common.data_models.trading.validate_order_fill") as mock_validate:
            OrderFill(price_cents=75, count=10, timestamp=now)

            mock_validate.assert_called_once_with(75, 10, now)


class TestOrderResponse:
    """Tests for OrderResponse dataclass."""

    def test_valid_creation_filled_order(self):
        """Test creating OrderResponse for filled order."""
        now = datetime.now(timezone.utc)
        fill1 = OrderFill(price_cents=DEFAULT_FILL_PRICE, count=5, timestamp=now)
        fill2 = OrderFill(price_cents=DEFAULT_FILL_PRICE + 1, count=5, timestamp=now)

        response = OrderResponse(
            order_id="exchange-order-456",
            client_order_id="order-123",
            status=OrderStatus.FILLED,
            ticker="KMARKT-25JAN01",
            side=OrderSide.YES,
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            filled_count=DEFAULT_FILLED_COUNT,
            remaining_count=DEFAULT_REMAINING_COUNT,
            average_fill_price_cents=DEFAULT_FILL_PRICE,
            timestamp=now,
            fees_cents=DEFAULT_FEES,
            fills=[fill1, fill2],
            trade_rule="TEMP_INCREASE",
            trade_reason="Temperature rising",
        )

        assert response.order_id == "exchange-order-456"
        assert response.client_order_id == "order-123"
        assert response.status == OrderStatus.FILLED
        assert response.ticker == "KMARKT-25JAN01"
        assert response.side == OrderSide.YES
        assert response.action == OrderAction.BUY
        assert response.order_type == OrderType.LIMIT
        assert response.filled_count == DEFAULT_FILLED_COUNT
        assert response.remaining_count == DEFAULT_REMAINING_COUNT
        assert response.average_fill_price_cents == DEFAULT_FILL_PRICE
        assert response.fees_cents == DEFAULT_FEES
        assert len(response.fills) == 2
        assert response.trade_rule == "TEMP_INCREASE"
        assert response.trade_reason == "Temperature rising"
        assert response.rejection_reason is None

    def test_valid_creation_rejected_order(self):
        """Test creating OrderResponse for rejected order."""
        now = datetime.now(timezone.utc)

        response = OrderResponse(
            order_id="exchange-order-456",
            client_order_id="order-123",
            status=OrderStatus.REJECTED,
            ticker="KMARKT-25JAN01",
            side=OrderSide.YES,
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            filled_count=ZERO_FILLED_COUNT,
            remaining_count=REJECTED_ORDER_REMAINING_COUNT,
            average_fill_price_cents=None,
            timestamp=now,
            fees_cents=0,
            fills=[],
            trade_rule="TEMP_INCREASE",
            trade_reason="Temperature rising",
            rejection_reason="Insufficient funds",
        )

        assert response.status == OrderStatus.REJECTED
        assert response.filled_count == ZERO_FILLED_COUNT
        assert response.remaining_count == 10
        assert response.average_fill_price_cents is None
        assert response.rejection_reason == "Insufficient funds"

    def test_validation_called_on_init(self):
        """Test that all validation functions are called."""
        now = datetime.now(timezone.utc)
        fills = [OrderFill(price_cents=DEFAULT_FILL_PRICE, count=DEFAULT_FILLED_COUNT, timestamp=now)]

        with patch("common.data_models.trading.validate_order_response_enums") as mock_enum_val:
            with patch("common.data_models.trading.validate_order_response_counts") as mock_count_val:
                with patch("common.data_models.trading.validate_order_response_price") as mock_price_val:
                    with patch("common.data_models.trading.validate_order_response_fills") as mock_fill_val:
                        with patch("common.data_models.trading.validate_order_response_metadata") as mock_meta_val:
                            OrderResponse(
                                order_id="exchange-order-456",
                                client_order_id="order-123",
                                status=OrderStatus.FILLED,
                                ticker="KMARKT-25JAN01",
                                side=OrderSide.YES,
                                action=OrderAction.BUY,
                                order_type=OrderType.LIMIT,
                                filled_count=DEFAULT_FILLED_COUNT,
                                remaining_count=DEFAULT_REMAINING_COUNT,
                                average_fill_price_cents=DEFAULT_FILL_PRICE,
                                timestamp=now,
                                fees_cents=DEFAULT_FEES,
                                fills=fills,
                                trade_rule="TEMP_INCREASE",
                                trade_reason="Temperature rising",
                            )

                            mock_enum_val.assert_called_once()
                            mock_count_val.assert_called_once()
                            mock_price_val.assert_called_once()
                            mock_fill_val.assert_called_once()
                            mock_meta_val.assert_called_once()


class TestTradingError:
    """Tests for TradingError dataclass."""

    def test_valid_creation_with_request_data(self):
        """Test creating TradingError with request data."""
        now = datetime.now(timezone.utc)
        request_data = {"ticker": "KMARKT-25JAN01", "count": 10}

        error = TradingError(
            error_code="INSUFFICIENT_FUNDS",
            error_message="Insufficient balance to place order",
            timestamp=now,
            operation_name="place_order",
            request_data=request_data,
        )

        assert error.error_code == "INSUFFICIENT_FUNDS"
        assert error.error_message == "Insufficient balance to place order"
        assert error.timestamp == now
        assert error.operation_name == "place_order"
        assert error.request_data == request_data

    def test_valid_creation_without_request_data(self):
        """Test creating TradingError without request data."""
        now = datetime.now(timezone.utc)

        error = TradingError(
            error_code="NETWORK_ERROR",
            error_message="Connection timeout",
            timestamp=now,
            operation_name="get_balance",
        )

        assert error.error_code == "NETWORK_ERROR"
        assert error.request_data is None

    def test_validation_called_on_init(self):
        """Test that validation is called during initialization."""
        now = datetime.now(timezone.utc)
        with patch("common.data_models.trading.validate_trading_error") as mock_validate:
            TradingError(
                error_code="TEST_ERROR",
                error_message="Test message",
                timestamp=now,
                operation_name="test_operation",
            )

            mock_validate.assert_called_once_with("TEST_ERROR", "Test message", "test_operation", now)


class TestMarketValidationData:
    """Tests for MarketValidationData dataclass."""

    def test_valid_creation_with_full_data(self):
        """Test creating MarketValidationData with all price data."""
        now = datetime.now(timezone.utc)

        data = MarketValidationData(
            ticker="KMARKT-25JAN01",
            is_open=True,
            best_bid_cents=74,
            best_ask_cents=76,
            last_price_cents=75,
            timestamp=now,
        )

        assert data.ticker == "KMARKT-25JAN01"
        assert data.is_open is True
        assert data.best_bid_cents == 74
        assert data.best_ask_cents == 76
        assert data.last_price_cents == 75
        assert data.timestamp == now

    def test_valid_creation_with_none_prices(self):
        """Test creating MarketValidationData with None prices (market closed)."""
        now = datetime.now(timezone.utc)

        data = MarketValidationData(
            ticker="KMARKT-25JAN01",
            is_open=False,
            best_bid_cents=None,
            best_ask_cents=None,
            last_price_cents=None,
            timestamp=now,
        )

        assert data.is_open is False
        assert data.best_bid_cents is None
        assert data.best_ask_cents is None
        assert data.last_price_cents is None

    def test_validation_called_on_init(self):
        """Test that validation is called during initialization."""
        now = datetime.now(timezone.utc)
        with patch("common.data_models.trading.validate_market_validation_data") as mock_validate:
            MarketValidationData(
                ticker="KMARKT-25JAN01",
                is_open=True,
                best_bid_cents=74,
                best_ask_cents=76,
                last_price_cents=75,
                timestamp=now,
            )

            mock_validate.assert_called_once_with("KMARKT-25JAN01", True, 74, 76, 75, now)
