"""Trade record construction from order execution data"""

from datetime import datetime

from common.truthy import pick_if

from ...data_models.trade_record import TradeRecord, TradeSide
from ...data_models.trading import OrderRequest, OrderResponse, OrderSide
from ..polling import PollingOutcome


def build_trade_record(
    order_request: OrderRequest,
    order_response: OrderResponse,
    outcome: PollingOutcome,
    market_category: str,
    weather_station: str,
    trade_timestamp: datetime,
) -> TradeRecord:
    """
    Build trade record from order execution data.

    Args:
        order_request: Original order request
        order_response: Order execution response
        outcome: Polling outcome with fill data
        market_category: Market category for record
        weather_station: Weather station identifier (may be empty)
        trade_timestamp: Trade execution timestamp

    Returns:
        Complete TradeRecord instance
    """
    trade_side = TradeSide.YES if order_request.side == OrderSide.YES else TradeSide.NO
    fee_cents = order_response.fees_cents
    if fee_cents is None:
        fee_cents = int()
    price_cents = outcome.average_price_cents
    if price_cents is None:
        price_cents = int()
    cost_cents = (price_cents * outcome.total_filled) + fee_cents

    trade_rule_value = order_request.trade_rule if hasattr(order_request, "trade_rule") else None
    trade_reason_value = order_request.trade_reason if hasattr(order_request, "trade_reason") else None
    trade_rule = pick_if(trade_rule_value is None, str, lambda: str(trade_rule_value))
    trade_reason = pick_if(trade_reason_value is None, str, lambda: str(trade_reason_value))

    return TradeRecord(
        order_id=order_response.order_id,
        market_ticker=order_request.ticker,
        trade_timestamp=trade_timestamp,
        trade_side=trade_side,
        quantity=outcome.total_filled,
        price_cents=price_cents,
        fee_cents=fee_cents,
        cost_cents=cost_cents,
        market_category=market_category,
        trade_rule=trade_rule,
        trade_reason=trade_reason,
        weather_station=weather_station,
    )
