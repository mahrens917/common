"""Trade record construction from order execution data"""

from datetime import datetime

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
    fee_cents = order_response.fees_cents or 0
    cost_cents = (outcome.average_price_cents * outcome.total_filled) + fee_cents

    trade_rule = getattr(order_request, "trade_rule", None)
    trade_reason = getattr(order_request, "trade_reason", None)

    return TradeRecord(
        order_id=order_response.order_id,
        market_ticker=order_request.ticker,
        trade_timestamp=trade_timestamp,
        trade_side=trade_side,
        quantity=outcome.total_filled,
        price_cents=outcome.average_price_cents,
        fee_cents=fee_cents,
        cost_cents=cost_cents,
        market_category=market_category,
        trade_rule=trade_rule or "",
        trade_reason=trade_reason or "",
        weather_station=weather_station,
    )
