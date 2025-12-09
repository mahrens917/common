"""P&L calculation logic for TradeRecord."""

from typing import TYPE_CHECKING, Optional

# Error messages
ERR_INVALID_PNL_VALUE = "PnL value must be numeric: {value}"

if TYPE_CHECKING:
    from ..trade_record import TradeRecord, TradeSide


def calculate_realised_pnl_cents(
    settlement_price_cents: Optional[int],
    trade_side: "TradeSide",
    quantity: int,
    cost_cents: int,
) -> Optional[int]:
    """Calculate realised P&L if the market has settled."""
    from ..trade_record import TradeSide

    if settlement_price_cents is None:
        return None

    if trade_side == TradeSide.YES:
        final_value = settlement_price_cents * quantity
    else:
        final_value = (100 - settlement_price_cents) * quantity

    return final_value - cost_cents


def get_current_market_price_cents(
    trade_side: "TradeSide",
    last_yes_bid: Optional[float],
    last_yes_ask: Optional[float],
) -> Optional[int]:
    """Calculate current market price based on trade side and available quotes."""
    from ..trade_record import TradeSide

    price: Optional[float]
    if trade_side == TradeSide.YES:
        price = last_yes_bid
    elif last_yes_ask is None:
        price = None
    else:
        price = 100 - float(last_yes_ask)

    if price is None:
        return None

    try:
        return int(round(float(price)))
    except (
        TypeError,
        ValueError,
    ):
        return None


def calculate_current_pnl_cents(
    trade: "TradeRecord",
) -> int:
    """Calculate current or realised P&L in cents."""

    realised = calculate_realised_pnl_cents(
        trade.settlement_price_cents,
        trade.trade_side,
        trade.quantity,
        trade.cost_cents,
    )
    if realised is not None:
        return realised

    current_price = get_current_market_price_cents(
        trade.trade_side,
        trade.last_yes_bid,
        trade.last_yes_ask,
    )
    if current_price is None:
        raise RuntimeError(
            f"Live market price unavailable for trade {trade.market_ticker}; cannot compute P&L"
        )

    return current_price * trade.quantity - trade.cost_cents
