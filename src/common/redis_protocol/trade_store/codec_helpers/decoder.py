"""Decoding functions for trade records."""

from datetime import datetime
from typing import Any, Dict, Union

import orjson

from ....data_models.trade_record import TradeRecord, TradeSide
from .field_extractor import ensure_timezone, extract_optional_fields
from .validators import validate_trade_data

JsonLike = Union[str, bytes, Dict[str, Any]]


def ensure_mapping(payload: JsonLike) -> Dict[str, Any]:
    """Convert payload to dictionary, parsing JSON if needed."""
    match payload:
        case dict():
            return payload
        case bytes():
            text_payload = payload.decode("utf-8")
        case str():
            text_payload = payload
        case _:
            raise TypeError(f"Unsupported payload type: {type(payload)!r}")

    try:
        return orjson.loads(text_payload)
    except orjson.JSONDecodeError as exc:
        raise ValueError("Trade payload is not valid JSON") from exc


def decode_trade_record(payload: JsonLike) -> TradeRecord:
    """Decode JSON payload into TradeRecord instance."""
    data = ensure_mapping(payload)
    validate_trade_data(data)
    optional_fields = extract_optional_fields(data)
    trade_timestamp = ensure_timezone(datetime.fromisoformat(data["trade_timestamp"]))

    return TradeRecord(
        order_id=data["order_id"],
        market_ticker=data["market_ticker"],
        trade_timestamp=trade_timestamp,
        trade_side=TradeSide(data["trade_side"]),
        quantity=int(data["quantity"]),
        price_cents=int(data["price_cents"]),
        fee_cents=int(data["fee_cents"]),
        cost_cents=int(data["cost_cents"]),
        trade_rule=data["trade_rule"],
        trade_reason=data["trade_reason"],
        weather_station=optional_fields["weather_station"],
        market_category=data["market_category"],
        last_yes_bid=optional_fields["last_yes_bid"],
        last_yes_ask=optional_fields["last_yes_ask"],
        last_price_update=optional_fields["last_price_update"],
        settlement_price_cents=optional_fields["settlement_price_cents"],
        settlement_time=optional_fields["settlement_time"],
    )
