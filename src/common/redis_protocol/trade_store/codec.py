from __future__ import annotations

"""
Serialisation helpers for trade store payloads.

The codec layer isolates schema validation logic from the Redis orchestration to
keep trade operations readable and to ensure data issues fail fast.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Union

import orjson

from ...data_models.trade_record import TradeRecord, TradeSide
from .codec_helpers.field_extractor import ensure_timezone, extract_optional_fields
from .codec_helpers.validators import validate_required_fields as _validate_required_fields
from .codec_helpers.validators import validate_trade_metadata as _validate_trade_metadata
from .codec_helpers.validators import validate_weather_fields as _validate_weather_fields
from .order_metadata_codec import OrderMetadataCodec

JsonLike = Union[str, bytes, Dict[str, Any]]


def _extract_optional_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    return extract_optional_fields(data)


def _decode_trade_record(payload: JsonLike) -> TradeRecord:
    data = _ensure_mapping(payload)
    _validate_required_fields(data)
    _validate_trade_metadata(data)
    _validate_weather_fields(data)

    optional_fields = _extract_optional_fields(data)
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


def _trade_to_payload(trade: TradeRecord) -> Dict[str, Any]:
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


def _ensure_mapping(payload: JsonLike) -> Dict[str, Any]:
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
    except orjson.JSONDecodeError as exc:  # pragma: no cover - caller handles
        raise ValueError("Trade payload is not valid JSON") from exc


@dataclass(frozen=True)
class TradeRecordCodec:
    """Encode and decode trade records for Redis storage."""

    def decode(self, payload: JsonLike) -> TradeRecord:
        return _decode_trade_record(payload)

    def encode(self, trade: TradeRecord) -> str:
        payload = _trade_to_payload(trade)
        return orjson.dumps(payload).decode("utf-8")

    def to_payload(self, trade: TradeRecord) -> Dict[str, Any]:
        return _trade_to_payload(trade)

    def to_mapping(self, payload: JsonLike) -> Dict[str, Any]:
        """Return the payload as a dictionary after JSON decoding."""
        return _ensure_mapping(payload)


__all__ = ["OrderMetadataCodec", "TradeRecordCodec"]
