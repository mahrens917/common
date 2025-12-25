from __future__ import annotations

from common.truthy import pick_if

"""Shared helpers for parsing Kalshi orderbook payloads."""

import logging
from typing import Any, Dict, Optional, Tuple

from common.exceptions import DataError

logger = logging.getLogger(__name__)

# Constants
_CONST_2 = 2


def merge_orderbook_payload(message: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
    """Flatten nested orderbook payload structures into a uniform dictionary."""
    msg_type = _extract_message_type(message)
    msg_data = _initialize_message_data(message)
    _merge_data_section(message, msg_data)
    market_ticker = _extract_market_ticker(msg_data)
    return msg_type, msg_data, market_ticker


def _extract_message_type(message: Dict[str, Any]) -> str:
    """Extract and normalize message type"""
    raw_type = message.get("type")
    return pick_if(raw_type is not None, lambda: str(raw_type), lambda: "")


def _initialize_message_data(message: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize message data from 'msg' field"""
    raw_msg = message.get("msg")
    if not isinstance(raw_msg, dict):
        return {}
    return {str(key): value for key, value in raw_msg.items()}


def _merge_data_section(message: Dict[str, Any], msg_data: Dict[str, Any]) -> None:
    """Merge nested data section into msg_data"""
    data_section = message.get("data")
    if not isinstance(data_section, dict):
        return

    _merge_orderbook_section(data_section, msg_data)
    _merge_levels_section(data_section, msg_data)
    _merge_remaining_fields(data_section, msg_data)


def _merge_orderbook_section(data_section: Dict[str, Any], msg_data: Dict[str, Any]) -> None:
    """Merge orderbook subsection"""
    orderbook_section = data_section.get("orderbook")
    if isinstance(orderbook_section, dict):
        msg_data.update({k: v for k, v in orderbook_section.items() if v is not None})


def _merge_levels_section(data_section: Dict[str, Any], msg_data: Dict[str, Any]) -> None:
    """Merge levels subsection"""
    levels_section = data_section.get("levels")
    if isinstance(levels_section, dict):
        msg_data.update({k: v for k, v in levels_section.items() if v is not None})


def _merge_remaining_fields(data_section: Dict[str, Any], msg_data: Dict[str, Any]) -> None:
    """Merge remaining data fields with normalization"""
    for key, value in data_section.items():
        if key in {"orderbook", "levels"} or value is None:
            continue
        if key in {"yes", "no"}:
            msg_data.setdefault(key, value)
        elif key == "bids" and "yes" not in msg_data:
            msg_data["yes"] = value
        elif key == "asks" and "no" not in msg_data:
            msg_data["no"] = value
        else:
            msg_data.setdefault(key, value)


def _extract_market_ticker(msg_data: Dict[str, Any]) -> str:
    """Extract and validate market ticker"""
    market_ticker = msg_data.get("market_ticker")
    if not market_ticker:
        raise ValueError("No market ticker in message")
    return str(market_ticker)


def build_snapshot_sides(msg_data: Dict[str, Any], market_ticker: str) -> Dict[str, Dict[str, float]]:
    """Convert yes/no level arrays into Redis hash compatible dictionaries."""

    orderbook_sides: Dict[str, Dict[str, float]] = {"yes_bids": {}, "yes_asks": {}}
    for side in ("yes", "no"):
        levels = _extract_levels(msg_data, side)
        if not levels:
            continue
        _populate_side_levels(orderbook_sides, side, levels, market_ticker)
    return orderbook_sides


def _extract_levels(msg_data: Dict[str, Any], side: str) -> Optional[list]:
    """Return level entries for the given side if present."""
    levels = msg_data.get(side)
    return levels if isinstance(levels, list) else None


def _populate_side_levels(
    orderbook_sides: Dict[str, Dict[str, float]],
    side: str,
    levels: list,
    market_ticker: str,
) -> None:
    """Populate orderbook entries for a given side."""
    for price_level in levels:
        price, size = _parse_price_level(price_level, market_ticker)
        if price is None or size is None:
            continue
        if side == "yes":
            orderbook_sides["yes_bids"][price] = size
        else:
            converted_price = str(100 - float(price))
            orderbook_sides["yes_asks"][converted_price] = size


def _parse_price_level(price_level: Any, market_ticker: str) -> Tuple[Optional[str], Optional[float]]:
    """Validate and convert a price level entry."""
    if not (isinstance(price_level, (list, tuple)) and len(price_level) == _CONST_2):
        raise DataError(f"Corrupted order book data detected for market {market_ticker}")

    price, size = price_level
    if not isinstance(size, (int, float)) or size <= 0:
        return None, None

    try:
        price_value = float(price)
    except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Expected data validation or parsing failure")
        return None, None

    price_str = f"{price_value:.1f}"
    return price_str, float(size)
