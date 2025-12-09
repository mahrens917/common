"""Metadata enrichment helpers."""

from typing import Any, Dict, Mapping, Optional

from ..kalshi_store.metadata_helpers.timestamp_normalization import normalize_timestamp


def enrich_strike_fields(
    enriched: Dict[str, Any],
    strike_type: str,
    floor_strike: Optional[float],
    cap_strike: Optional[float],
    strike_value: Optional[float],
) -> None:
    """Enrich metadata with strike-related fields."""
    _ensure_strike_type(enriched, strike_type)
    _ensure_strike_value(enriched, strike_value)

    if strike_type == "greater":
        _apply_greater_defaults(enriched, floor_strike)
    elif strike_type == "less":
        _apply_less_defaults(enriched, cap_strike)
    elif strike_type == "between":
        _apply_between_defaults(enriched)


def enrich_close_time(enriched: Dict[str, Any], metadata: Mapping[str, Any]) -> None:
    """Enrich metadata with normalized close_time."""
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


def enrich_orderbook_defaults(enriched: Dict[str, Any]) -> None:
    """Add default empty orderbook fields if missing."""
    orderbook_fields = ["yes_bids", "yes_asks", "no_bids", "no_asks"]
    for field in orderbook_fields:
        if field not in enriched:
            enriched[field] = "{}"


def enrich_status_field(enriched: Dict[str, Any], metadata: Mapping[str, Any]) -> None:
    """Add status field with default if missing."""
    if "status" not in enriched:
        if "status" in metadata:
            enriched["status"] = metadata["status"]
        else:
            enriched["status"] = "open"


def _ensure_strike_type(enriched: Dict[str, Any], strike_type: str) -> None:
    """Set strike type when missing."""
    if not enriched.get("strike_type"):
        enriched["strike_type"] = strike_type


def _ensure_strike_value(enriched: Dict[str, Any], strike_value: Optional[float]) -> None:
    """Populate strike value when available."""
    if strike_value is not None and not enriched.get("strike"):
        enriched["strike"] = str(strike_value)


def _apply_greater_defaults(enriched: Dict[str, Any], floor_strike: Optional[float]) -> None:
    """Set defaults for GREATER markets."""
    if floor_strike is not None and not enriched.get("floor_strike"):
        enriched["floor_strike"] = str(floor_strike)
    if not enriched.get("cap_strike"):
        enriched["cap_strike"] = "inf"


def _apply_less_defaults(enriched: Dict[str, Any], cap_strike: Optional[float]) -> None:
    """Set defaults for LESS markets."""
    if cap_strike is not None and not enriched.get("cap_strike"):
        enriched["cap_strike"] = str(cap_strike)
    if not enriched.get("floor_strike"):
        enriched["floor_strike"] = "0"


def _apply_between_defaults(enriched: Dict[str, Any]) -> None:
    """Ensure BETWEEN markets expose bounds."""
    if "floor_strike" not in enriched:
        enriched["floor_strike"] = ""
    if "cap_strike" not in enriched:
        enriched["cap_strike"] = ""
