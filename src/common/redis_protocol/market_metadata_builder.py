from __future__ import annotations

"""Helpers for constructing Kalshi market metadata payloads."""

import logging
import time
from typing import Any, Dict, Mapping, Optional

import orjson
from orjson import JSONEncodeError

from ..redis_schema import KalshiMarketDescriptor
from .market_normalization import normalize_timestamp
from .weather_station_resolver import WeatherStationResolver

_TIME_FIELD_KEYS = {
    "open_time": "open_time",
    "expected_expiration_time": "expected_expiration_time",
    "expiration_time": "expiration_time",
    "latest_expiration_time": "latest_expiration_time",
    "fee_waiver_expiration_time": "fee_waiver_expiration_time",
}

_NUMERIC_FIELDS = {
    "tick_size": 0,
    "last_price": 0,
    "previous_price": 0,
    "settlement_value": 0,
    "settlement_timer_seconds": 0,
    "volume": 0,
    "volume_24h": 0,
    "open_interest": 0,
    "liquidity": 0,
    "notional_value": 0,
    "previous_yes_bid": 0,
    "previous_yes_ask": 0,
    "risk_limit_cents": 0,
    "functional_strike": 0,
    "custom_strike": 0,
    "min_tick_size": 0,
    "max_tick_size": 0,
    "dollar_volume_24h": 0,
    "volume_24h_change": 0,
    "open_interest_change": 0,
    "price_change_24h": 0,
    "price_change_percent_24h": 0,
    "high_24h": 0,
    "low_24h": 0,
    "trades_24h": 0,
    "unique_traders_24h": 0,
}

_STRING_FIELDS = {
    "status": "",
    "result": "",
    "response_price_units": "",
    "title": "",
    "subtitle": "",
    "yes_sub_title": "",
    "no_sub_title": "",
    "category": "",
    "rules_primary": "",
    "rules_secondary": "",
    "market_type": "",
    "event_id": "",
    "series_id": "",
    "underlying": "",
    "ranged_group_id": "",
}

_ORDER_BOOK_FIELDS = [
    "yes_bid",
    "yes_ask",
    "no_bid",
    "no_ask",
    "yes_bid_size",
    "yes_ask_size",
    "no_bid_size",
    "no_ask_size",
]

_ORDER_BOOK_JSON_FIELDS = [
    "yes_bids",
    "yes_asks",
    "no_bids",
    "no_asks",
]


def _stringify(value: Any) -> str:
    if value is None:
        _none_guard_value = ""
        return _none_guard_value
    if isinstance(value, bool):
        if value:
            return "true"
        return "false"
    return str(value)


def _stringify_json(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value
    try:
        return orjson.dumps(value).decode("utf-8")
    except (JSONEncodeError, TypeError) as exc:  # policy_guard: allow-silent-handler
        raise ValueError(f"Unable to serialise value to JSON: {value!r}") from exc


def _value_or_default(mapping: Mapping[str, Any], key: str, alternate: Any) -> Any:
    return mapping[key] if key in mapping else alternate


def _resolve_weather_station(
    market_ticker: str,
    resolver: Optional[WeatherStationResolver],
    logger: logging.Logger,
) -> Optional[str]:
    if resolver is None:
        return None
    return resolver.extract_station(market_ticker)


def _normalise_timestamp_optional(value: Any) -> str:
    if value in (None, ""):
        return ""
    normalized = normalize_timestamp(value)
    if not normalized:
        return ""
    return normalized


def _extract_time_fields(market_data: Mapping[str, Any]) -> Dict[str, str]:
    close_time_raw = market_data.get("close_time")
    if close_time_raw is None:
        close_time_raw = market_data.get("close_time_ts")
    if close_time_raw is None:
        raise ValueError("close_time missing from Kalshi payload")

    close_time_value = ""
    if close_time_raw != "":
        normalized_close_time = normalize_timestamp(close_time_raw)
        if normalized_close_time:
            close_time_value = normalized_close_time

    time_fields: Dict[str, str] = {
        "close_time": close_time_value,
    }

    for target_key, source_key in _TIME_FIELD_KEYS.items():
        time_fields[target_key] = _normalise_timestamp_optional(market_data.get(source_key))

    return time_fields


def _extract_strike_fields(
    ticker: str,
    strike_type_raw: Any,
    floor_strike_api: Any,
    cap_strike_api: Any,
) -> Dict[str, str]:
    if not isinstance(strike_type_raw, str):
        raise TypeError(f"strike_type must be provided for {ticker}")
    strike_type_key = strike_type_raw.lower()

    if strike_type_key not in {"greater", "less", "between"}:
        raise TypeError(f"Unsupported strike_type '{strike_type_raw}' in Kalshi payload")

    if strike_type_key == "greater":
        if floor_strike_api is None:
            raise ValueError(f"floor_strike missing for 'greater' market {ticker}")
        floor_strike_value = _stringify(floor_strike_api)
        cap_strike_value = "inf"
    elif strike_type_key == "less":
        if cap_strike_api is None:
            raise ValueError(f"cap_strike missing for 'less' market {ticker}")
        floor_strike_value = "0"
        cap_strike_value = _stringify(cap_strike_api)
    else:  # between
        if floor_strike_api is None or cap_strike_api is None:
            raise ValueError(f"floor_strike/cap_strike missing for 'between' market {ticker}")
        floor_strike_value = _stringify(floor_strike_api)
        cap_strike_value = _stringify(cap_strike_api)

    return {
        "strike_type": _stringify(strike_type_raw),
        "floor_strike": floor_strike_value,
        "cap_strike": cap_strike_value,
    }


def _build_core_metadata(
    canonical_ticker: str,
    market_data: Mapping[str, Any],
    weather_resolver: Optional[WeatherStationResolver],
    logger: logging.Logger,
    time_fields: Dict[str, str],
    strike_fields: Dict[str, str],
) -> Dict[str, str]:
    """Construct the base metadata payload."""
    weather_station = _resolve_weather_station(canonical_ticker, weather_resolver, logger)
    metadata: Dict[str, str] = {
        "market_ticker": canonical_ticker,
        "market_id": _stringify(market_data.get("id")),
        **time_fields,
        **strike_fields,
        "timestamp": str(int(time.time())),
    }
    can_close_early_value = _value_or_default(market_data, "can_close_early", False)
    metadata["can_close_early"] = _stringify(can_close_early_value).lower()
    if weather_station:
        metadata["weather_station"] = weather_station
    return metadata


def _populate_numeric_fields(metadata: Dict[str, str], market_data: Mapping[str, Any]) -> None:
    """Populate numeric fields with defaults."""
    for field, option_value in _NUMERIC_FIELDS.items():
        value = _value_or_default(market_data, field, option_value)
        metadata[field] = _stringify(value)


def _populate_string_fields(metadata: Dict[str, str], market_data: Mapping[str, Any]) -> None:
    """Populate string fields with defaults."""
    for field, option_value in _STRING_FIELDS.items():
        value = _value_or_default(market_data, field, option_value)
        metadata[field] = _stringify(value)


def _populate_orderbook_fields(metadata: Dict[str, str], market_data: Mapping[str, Any]) -> None:
    """Inject orderbook price/size fields."""
    for field in _ORDER_BOOK_FIELDS:
        metadata[field] = _stringify(market_data.get(field))

    for field in _ORDER_BOOK_JSON_FIELDS:
        metadata[field] = _stringify_json(market_data.get(field))


def _apply_descriptor_defaults(metadata: Dict[str, str], descriptor: KalshiMarketDescriptor) -> None:
    """Apply descriptor values for ticker/category/etc when not already set."""
    metadata.setdefault("ticker", descriptor.ticker)
    metadata.setdefault("category", descriptor.category.value)
    if descriptor.underlying and not metadata.get("underlying"):
        metadata["underlying"] = descriptor.underlying
    if descriptor.expiry_token:
        metadata.setdefault("expiry_token", descriptor.expiry_token)


def _populate_event_metadata(metadata: Dict[str, str], event_data: Optional[Mapping[str, Any]]) -> None:
    """Populate event-specific fields when event data is available."""
    if not event_data:
        return

    metadata.update(
        {
            "event_ticker": _stringify(event_data.get("ticker")),
            "event_title": _stringify(event_data.get("title")),
            "event_name": _stringify(event_data.get("name")),
            "event_category": _stringify(event_data.get("category")),
            "series_ticker": _stringify(event_data.get("series_ticker")),
            "strike_date": _stringify(event_data.get("strike_date")),
            "event_type": _stringify(event_data.get("event_type")),
            "event_subtitle": _stringify(event_data.get("sub_title")),
            "strike_period": _stringify(event_data.get("strike_period")),
            "mutually_exclusive": _stringify(_value_or_default(event_data, "mutually_exclusive", False)).lower(),
            "collateral_return_type": _stringify(event_data.get("collateral_return_type")),
            "event_description": _stringify(event_data.get("description")),
            "event_tags": _stringify(_value_or_default(event_data, "tags", [])),
            "event_status": _stringify(event_data.get("status")),
            "event_created_time": _stringify(event_data.get("created_time")),
            "event_modified_time": _stringify(event_data.get("modified_time")),
        }
    )


def build_market_metadata(
    *,
    market_ticker: str,
    market_data: Mapping[str, Any],
    event_data: Optional[Mapping[str, Any]],
    descriptor: KalshiMarketDescriptor,
    weather_resolver: Optional[WeatherStationResolver],
    logger: logging.Logger,
) -> Dict[str, str]:
    """
    Construct a metadata dictionary using Kalshi REST payloads.

    The builder focuses exclusively on REST-provided fields so downstream weather/trading
    enrichments remain untouched.
    """

    canonical_ticker = descriptor.ticker
    time_fields = _extract_time_fields(market_data)
    strike_fields = _extract_strike_fields(
        canonical_ticker,
        market_data.get("strike_type"),
        market_data.get("floor_strike"),
        market_data.get("cap_strike"),
    )

    metadata = _build_core_metadata(
        canonical_ticker,
        market_data,
        weather_resolver,
        logger,
        time_fields,
        strike_fields,
    )

    _populate_numeric_fields(metadata, market_data)
    _populate_string_fields(metadata, market_data)
    _populate_orderbook_fields(metadata, market_data)
    _apply_descriptor_defaults(metadata, descriptor)
    _populate_event_metadata(metadata, event_data)

    return metadata


__all__ = ["build_market_metadata"]
