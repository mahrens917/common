"""Expiry/timestamp helpers for market normalization."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Mapping, Optional

from common.exceptions import DataError

from ..redis_schema import KalshiMarketDescriptor
from .kalshi_store.metadata_helpers.expiry_derivation import derive_expiry_iso_impl
from .kalshi_store.metadata_helpers.timestamp_normalization import select_timestamp_value
from .market_normalization_core import derive_strike_fields
from .market_normalization_helpers import (
    enrich_close_time,
    enrich_orderbook_defaults,
    enrich_status_field,
    enrich_strike_fields,
)


def derive_expiry_iso(
    market_ticker: str,
    metadata: Mapping[str, Any],
    *,
    descriptor: KalshiMarketDescriptor,
    token_parser: Optional[Callable[..., Optional[datetime]]] = None,
    now: Optional[datetime] = None,
) -> str:
    """Ensure we have an ISO formatted expiry/close time for downstream consumers."""
    try:
        return derive_expiry_iso_impl(
            market_ticker,
            dict(metadata),
            descriptor.expiry_token,
            now_dt=now,
            token_parser=token_parser,
        )
    except (
        DataError,
        RuntimeError,
    ) as exc:
        raise ExpiryDerivationError(str(exc)) from exc


def ensure_market_metadata_fields(
    market_ticker: str,
    metadata: Mapping[str, Any],
    *,
    descriptor: KalshiMarketDescriptor,
    token_parser: Optional[Callable[[str], Optional[datetime]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Populate essential metadata fields when REST ingestion is missing."""
    enriched = dict(metadata)
    enriched.setdefault("ticker", market_ticker)

    # Enrich strike fields from ticker
    strike_details = derive_strike_fields(market_ticker)
    if strike_details is not None:
        strike_type, floor_strike, cap_strike, strike_value = strike_details
        enrich_strike_fields(enriched, strike_type, floor_strike, cap_strike, strike_value)

    # Enrich close time
    enrich_close_time(enriched, metadata)

    # Add default orderbook fields
    enrich_orderbook_defaults(enriched)

    # Add status field
    enrich_status_field(enriched, metadata)

    return enriched


__all__ = [
    "derive_expiry_iso",
    "ensure_market_metadata_fields",
    "select_timestamp_value",
]


class ExpiryDerivationError(DataError, RuntimeError):
    """Raised when expiry cannot be derived from provided metadata."""
