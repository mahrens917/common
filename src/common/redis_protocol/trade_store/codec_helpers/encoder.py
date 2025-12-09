"""Encoding functions for trade records."""

from typing import Any, Dict

import orjson

from ....data_models.trade_record import TradeRecord


def trade_record_to_payload(trade: TradeRecord) -> Dict[str, Any]:
    """Convert TradeRecord to dictionary payload."""
    payload: Dict[str, Any] = {
        "order_id": trade.order_id,
        "market_ticker": trade.market_ticker,
        "trade_timestamp": trade.trade_timestamp.isoformat(),
        "trade_side": trade.trade_side.value,
        "quantity": trade.quantity,
        "price_cents": trade.price_cents,
        "fee_cents": trade.fee_cents,
        "cost_cents": trade.cost_cents,
        "market_category": trade.market_category,
        "trade_rule": trade.trade_rule,
        "trade_reason": trade.trade_reason,
    }
    if trade.weather_station is not None:
        payload["weather_station"] = trade.weather_station
    if trade.settlement_price_cents is not None:
        payload["settlement_price_cents"] = trade.settlement_price_cents
    if trade.settlement_time is not None:
        payload["settlement_time"] = trade.settlement_time.isoformat()
    if trade.last_yes_bid is not None:
        payload["last_yes_bid"] = trade.last_yes_bid
    if trade.last_yes_ask is not None:
        payload["last_yes_ask"] = trade.last_yes_ask
    if trade.last_price_update is not None:
        payload["last_price_update"] = trade.last_price_update.isoformat()
    return payload


def encode_trade_record(trade: TradeRecord) -> str:
    """Encode TradeRecord to JSON string."""
    payload = trade_record_to_payload(trade)
    return orjson.dumps(payload).decode("utf-8")
