from __future__ import annotations

"""Metadata field enrichment and validation."""

from typing import Any, Dict, Optional

from ...parsing import derive_strike_fields
from .timestamp_normalization import normalize_timestamp


def enrich_metadata_fields(market_ticker: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Populate essential metadata fields when REST ingestion is missing data.

    Enriches:
    - ticker field (defaults to market_ticker)
    - strike_type, floor_strike, cap_strike, strike (derived from ticker)
    - close_time (normalized to ISO8601)
    - order book fields (yes_bids, yes_asks, no_bids, no_asks)
    - status (defaults to "open")

    Args:
        market_ticker: Market ticker symbol
        metadata: Existing metadata dictionary

    Returns:
        Enriched metadata dictionary
    """
    enriched = dict(metadata)
    enriched.setdefault("ticker", market_ticker)

    _enrich_strike_fields(market_ticker, enriched)
    _enrich_close_time(enriched)
    _enrich_order_book_fields(enriched)
    _enrich_status_field(metadata, enriched)

    return enriched


def _enrich_strike_fields(market_ticker: str, enriched: Dict[str, Any]) -> None:
    """Enrich strike-related fields from ticker parsing."""
    strike_details = derive_strike_fields(market_ticker)
    if strike_details is None:
        return

    strike_type, floor_strike, cap_strike, strike_value = strike_details
    _set_base_strike_fields(enriched, strike_type, strike_value)
    _set_type_specific_strike_bounds(enriched, strike_type, floor_strike, cap_strike)


def _set_base_strike_fields(
    enriched: Dict[str, Any], strike_type: str, strike_value: Optional[float]
) -> None:
    """Set strike_type and strike value if missing"""
    if not enriched.get("strike_type"):
        enriched["strike_type"] = strike_type
    if strike_value is not None and not enriched.get("strike"):
        enriched["strike"] = str(strike_value)


def _set_type_specific_strike_bounds(
    enriched: Dict[str, Any],
    strike_type: str,
    floor_strike: Optional[float],
    cap_strike: Optional[float],
) -> None:
    """Set floor/cap bounds based on strike type"""
    if strike_type == "greater":
        _set_greater_strike_bounds(enriched, floor_strike)
    elif strike_type == "less":
        _set_less_strike_bounds(enriched, cap_strike)
    elif strike_type == "between":
        _set_between_strike_bounds(enriched)


def _set_greater_strike_bounds(enriched: Dict[str, Any], floor_strike: Optional[float]) -> None:
    """Set bounds for 'greater' type markets"""
    if floor_strike is not None and not enriched.get("floor_strike"):
        enriched["floor_strike"] = str(floor_strike)
    if not enriched.get("cap_strike"):
        enriched["cap_strike"] = "inf"


def _set_less_strike_bounds(enriched: Dict[str, Any], cap_strike: Optional[float]) -> None:
    """Set bounds for 'less' type markets"""
    if cap_strike is not None and not enriched.get("cap_strike"):
        enriched["cap_strike"] = str(cap_strike)
    if not enriched.get("floor_strike"):
        enriched["floor_strike"] = "0"


def _set_between_strike_bounds(enriched: Dict[str, Any]) -> None:
    """Set bounds for 'between' type markets"""
    if "floor_strike" not in enriched:
        enriched["floor_strike"] = ""
    if "cap_strike" not in enriched:
        enriched["cap_strike"] = ""


def _enrich_close_time(enriched: Dict[str, Any]) -> None:
    """Normalize and enrich close_time field."""
    close_time_value = enriched.get("close_time")
    if close_time_value not in (None, ""):
        normalized_close = normalize_timestamp(close_time_value)
        if normalized_close:
            enriched["close_time"] = normalized_close
    else:
        candidate = enriched.get("close_time_ms")
        if isinstance(candidate, str) and candidate.isdigit():
            candidate = int(candidate)
        normalized_close = normalize_timestamp(candidate)
        if normalized_close:
            enriched["close_time"] = normalized_close


def _enrich_order_book_fields(enriched: Dict[str, Any]) -> None:
    """Ensure order book fields exist with empty defaults."""
    if "yes_bids" not in enriched:
        enriched["yes_bids"] = "{}"
    if "yes_asks" not in enriched:
        enriched["yes_asks"] = "{}"
    if "no_bids" not in enriched:
        enriched["no_bids"] = "{}"
    if "no_asks" not in enriched:
        enriched["no_asks"] = "{}"


def _enrich_status_field(metadata: Dict[str, Any], enriched: Dict[str, Any]) -> None:
    """Ensure status field exists with default value."""
    if "status" not in enriched:
        status_value = metadata.get("status")
        if status_value is None:
            status_value = "open"
        enriched["status"] = status_value
