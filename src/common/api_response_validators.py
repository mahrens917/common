"""
Kalshi API Response Validators

This module provides strict validation for all Kalshi API responses.
No default values or inferred substitutes - fail fast on any mismatch.
"""

from typing import Any, Dict, List, Optional

from .api_response_validators_helpers import (
    validate_event_markets_field,
    validate_event_required_fields,
    validate_event_string_fields,
    validate_event_wrapper,
    validate_market_numeric_fields,
    validate_market_price_fields,
    validate_market_status,
    validate_market_strings,
    validate_market_timestamps,
    validate_order_enum_fields,
    validate_order_numeric_fields,
    validate_order_prices,
    validate_order_strings,
    validate_order_timestamps,
    validate_required_fields,
    validate_series_item,
    validate_series_optional_fields,
    validate_series_strings,
)

# Constants
_CONST_NEG_1000000000 = -1000000000


def validate_portfolio_balance_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate portfolio balance API response.

    Expected structure (actual Kalshi API):
    {
        "balance": 10000  # in cents, just an integer
    }
    """
    if not response_data:
        raise ValueError("Empty response from portfolio balance API")

    if "balance" not in response_data:
        raise ValueError(
            f"Missing 'balance' field in response. "
            f"Available fields: {list(response_data.keys())}"
        )

    balance_value = response_data["balance"]

    # Validate type - should be numeric
    if not isinstance(balance_value, (int, float)):
        raise TypeError("Balance must be numeric")

    # Validate range - balance can be negative (if in debt), but let's validate it's reasonable
    if balance_value < _CONST_NEG_1000000000:  # -$10,000 reasonable debt limit
        raise ValueError(f"Balance unreasonably negative: {balance_value} cents")

    return {"balance": balance_value}


def validate_market_object(market_data: Any, index: Optional[int] = None) -> Dict[str, Any]:
    """
    Validate a single market object from the markets API.

    Expected fields:
    - ticker: Market identifier
    - event_ticker: Parent event ticker
    - title: Market title
    - open_time: ISO timestamp
    - close_time: ISO timestamp
    - status: Market status (open/closed/settled)
    - yes_bid: Current yes bid price (may be null)
    - yes_ask: Current yes ask price (may be null)
    - no_bid: Current no bid price (may be null)
    - no_ask: Current no ask price (may be null)
    - last_price: Last traded price (may be null)
    - volume: Total volume traded
    - volume_24h: 24-hour volume
    """
    prefix = f"Market {index}: " if index is not None else ""

    if not isinstance(market_data, dict):
        raise TypeError(f"{prefix}Market data must be dict, got: {type(market_data)}")

    required_fields = [
        "ticker",
        "event_ticker",
        "title",
        "open_time",
        "close_time",
        "status",
        "volume",
        "volume_24h",
    ]

    validate_required_fields(market_data, required_fields, prefix)
    validate_market_strings(market_data, prefix)
    validate_market_status(market_data, prefix)
    validate_market_timestamps(market_data, prefix)
    validate_market_numeric_fields(market_data, prefix)
    validate_market_price_fields(market_data, prefix)

    return market_data


def validate_markets_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate markets API response.

    Expected structure:
    {
        "markets": [...],
        "cursor": "next_page_cursor"  # optional
    }
    """
    if not response_data:
        raise ValueError("Empty response from markets API")

    if "markets" not in response_data:
        raise ValueError(
            f"Missing 'markets' field in response. "
            f"Available fields: {list(response_data.keys())}"
        )

    markets = response_data["markets"]

    if not isinstance(markets, list):
        raise TypeError("Markets must be a list")

    # Validate each market object
    validated_markets = []
    for idx, market in enumerate(markets):
        validated_market = validate_market_object(market, idx)
        validated_markets.append(validated_market)

    # Cursor is optional but if present must be string
    if "cursor" in response_data:
        if response_data["cursor"] is not None and not isinstance(response_data["cursor"], str):
            raise ValueError(f"Cursor must be string or null, got: {type(response_data['cursor'])}")

    return {"markets": validated_markets, "cursor": response_data.get("cursor")}


def validate_event_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate event API response.

    Expected structure:
    {
        "event": {
            "ticker": "EVENT-2024",
            "title": "Event Title",
            "category": "weather",
            "series_ticker": "SERIES-2024",
            "markets": [...]  # optional, if with_nested_markets=true
        }
    }
    """
    event_data = validate_event_wrapper(response_data)
    validate_event_required_fields(event_data)
    validate_event_string_fields(event_data)
    _validate_event_markets(event_data)
    return event_data


def _validate_event_markets(event_data: Dict[str, Any]) -> None:
    """Validate nested markets when present."""
    if not validate_event_markets_field(event_data):
        return

    event_data["markets"] = [
        validate_market_object(market, idx) for idx, market in enumerate(event_data["markets"])
    ]


def validate_series_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate series API response.

    Expected structure:
    {
        "series": [
            {
                "ticker": "SERIES-2024",
                "title": "Series Title",
                "category": "weather",
                "frequency": "daily",
                "status": "active"
            }
        ]
    }
    """
    if not response_data:
        raise ValueError("Empty response from series API")

    if "series" not in response_data:
        raise ValueError(
            f"Missing 'series' field in response. "
            f"Available fields: {list(response_data.keys())}"
        )

    series_list = response_data["series"]

    if not isinstance(series_list, list):
        raise TypeError("Series must be a list")

    validated_series = []
    for idx, series_data in enumerate(series_list):
        if not isinstance(series_data, dict):
            raise TypeError(f"Series {idx} must be dict, got: {type(series_data)}")
        validate_series_item(series_data, idx)
        validate_series_strings(series_data, idx)
        validate_series_optional_fields(series_data, idx)
        validated_series.append(series_data)

    return validated_series


def validate_cancel_order_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate cancel order API response.

    Expected structure (Kalshi API returns the canceled order):
    {
        "order": {
            "order_id": "string",
            "market_ticker": "string",
            "status": "canceled",
            "client_order_id": "string",
            "side": "<side>",
            "type": "<order_type>",
            "action": "<action>",
            "count": integer,
            "yes_price": integer (optional for market orders),
            "no_price": integer (optional for market orders),
            "created_time": "ISO timestamp",
            "expiration_time": "ISO timestamp" (optional)
        }
    }

    Notes:
        - side must be in {"yes", "no"}
        - type must be in {"limit", "market"}
        - action must be in {"buy", "sell"}

    Or sometimes just the order object directly without wrapper.
    """
    if not response_data:
        raise ValueError("Empty response from cancel order API")

    # Check if response has 'order' wrapper or is direct order object
    order_data = response_data.get("order", response_data)

    if not isinstance(order_data, dict):
        raise TypeError(f"Order data must be dict, got: {type(order_data)}")

    required_fields = [
        "order_id",
        "market_ticker",
        "status",
        "side",
        "type",
        "action",
        "count",
        "created_time",
    ]

    validate_required_fields(order_data, required_fields, "")

    # Validate status is 'canceled'
    if order_data["status"] not in ["canceled", "cancelled"]:
        raise ValueError(
            f"Expected status 'canceled' for cancel response, got: '{order_data['status']}'"
        )

    validate_order_strings(order_data)
    validate_order_enum_fields(order_data)
    validate_order_numeric_fields(order_data)
    validate_order_timestamps(order_data)
    validate_order_prices(order_data)

    return order_data


def validate_exchange_status_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate exchange status API response.

    Expected structure (direct fields, no wrapper):
    {
        "trading_active": true,
        "exchange_active": true
    }
    """
    if not response_data:
        raise ValueError("Empty response from exchange status API")

    # The actual API returns fields directly, no 'exchange' wrapper
    # Validate required fields
    required_fields = ["trading_active", "exchange_active"]
    missing_fields = [field for field in required_fields if field not in response_data]

    if missing_fields:
        raise ValueError(
            f"Missing required fields in exchange status: {missing_fields}. "
            f"Available fields: {list(response_data.keys())}"
        )

    # Validate boolean fields
    for field in required_fields:
        if not isinstance(response_data[field], bool):
            raise TypeError(f"Exchange {field} must be boolean")

    return response_data
