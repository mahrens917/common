"""Build metadata fields from market and event data."""

import logging
from typing import Any, Dict, Mapping

logger = logging.getLogger(__name__)


def build_time_fields(market_data: Mapping[str, Any], time_field_keys: Dict[str, str], normalizer: Any) -> Dict[str, str]:
    """
    Build time-related fields from market data.

    Args:
        market_data: Market data from API
        time_field_keys: Mapping of time field keys
        normalizer: Timestamp normalization function

    Returns:
        Dict of time fields
    """
    close_time_raw = market_data.get("close_time") or market_data.get("close_time_ts")
    if close_time_raw is None:
        raise ValueError("close_time missing from Kalshi payload")

    close_time_value = ""
    if close_time_raw != "":
        normalized_close_time = normalizer(close_time_raw)
        if normalized_close_time:
            close_time_value = normalized_close_time

    time_fields: Dict[str, str] = {"close_time": close_time_value}

    for target_key, source_key in time_field_keys.items():
        time_fields[target_key] = _normalise_timestamp_optional(market_data.get(source_key), normalizer)

    return time_fields


def _normalise_timestamp_optional(value: Any, normalizer: Any) -> str:
    """Normalize timestamp with None handling."""
    if value in (None, ""):
        return ""
    normalized = normalizer(value)
    if not normalized:
        return ""
    return normalized


def build_numeric_fields(market_data: Mapping[str, Any], numeric_fields: Dict[str, Any], stringify_func: Any) -> Dict[str, str]:
    """Build numeric fields with option values."""
    result = {}
    for field, option_value in numeric_fields.items():
        value = market_data.get(field, option_value)
        result[field] = stringify_func(value)
    return result


def build_string_fields(market_data: Mapping[str, Any], string_fields: Dict[str, str], stringify_func: Any) -> Dict[str, str]:
    """Build string fields with option values."""
    result = {}
    for field, option_value in string_fields.items():
        value = market_data.get(field, option_value)
        result[field] = stringify_func(value)
    return result


def build_orderbook_fields(market_data: Mapping[str, Any], orderbook_fields: list, stringify_func: Any) -> Dict[str, str]:
    """Build orderbook fields."""
    result = {}
    for field in orderbook_fields:
        result[field] = stringify_func(market_data.get(field))
    return result


def build_orderbook_json_fields(market_data: Mapping[str, Any], json_fields: list, json_stringify_func: Any) -> Dict[str, str]:
    """Build orderbook JSON fields."""
    result = {}
    for field in json_fields:
        result[field] = json_stringify_func(market_data.get(field))
    return result


def build_event_fields(event_data: Mapping[str, Any], stringify_func: Any, value_or_default_func: Any) -> Dict[str, str]:
    """Build event-related metadata fields."""
    return {
        "event_ticker": stringify_func(event_data.get("ticker")),
        "event_title": stringify_func(event_data.get("title")),
        "event_name": stringify_func(event_data.get("name")),
        "event_category": stringify_func(event_data.get("category")),
        "series_ticker": stringify_func(event_data.get("series_ticker")),
        "strike_date": stringify_func(event_data.get("strike_date")),
        "event_type": stringify_func(event_data.get("event_type")),
        "event_subtitle": stringify_func(event_data.get("sub_title")),
        "strike_period": stringify_func(event_data.get("strike_period")),
        "mutually_exclusive": stringify_func(value_or_default_func(event_data, "mutually_exclusive", False)).lower(),
        "collateral_return_type": stringify_func(event_data.get("collateral_return_type")),
        "event_description": stringify_func(event_data.get("description")),
        "event_tags": stringify_func(value_or_default_func(event_data, "tags", [])),
        "event_status": stringify_func(event_data.get("status")),
        "event_created_time": stringify_func(event_data.get("created_time")),
        "event_modified_time": stringify_func(event_data.get("modified_time")),
    }


def add_descriptor_fields(metadata: Dict[str, str], descriptor: Any) -> None:
    """Add descriptor fields to metadata in-place."""
    if "ticker" not in metadata:
        metadata["ticker"] = descriptor.ticker
    if not metadata.get("category"):
        metadata["category"] = descriptor.category.value
    if descriptor.underlying and not metadata.get("underlying"):
        metadata["underlying"] = descriptor.underlying
    if descriptor.expiry_token:
        metadata.setdefault("expiry_token", descriptor.expiry_token)
