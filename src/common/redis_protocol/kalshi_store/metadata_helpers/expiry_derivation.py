from __future__ import annotations

"""Expiry date derivation logic."""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from src.common.exceptions import DataError

from ...parsing import parse_expiry_token


def _normalize_iso(iso_value: str) -> str:
    """Convert trailing 'Z' to '+00:00' for consistency."""
    return iso_value[:-1] + "+00:00" if iso_value.endswith("Z") else iso_value


def derive_expiry_iso_impl(
    market_ticker: str,
    metadata: Dict[str, Any],
    descriptor_expiry_token: Optional[str],
    *,
    now_dt: Optional[datetime] = None,
    token_parser: Optional[Callable[..., Optional[datetime]]] = None,
) -> str:
    """
    Derive an ISO8601 expiry for a market when Kalshi REST metadata is incomplete.

    Attempts to derive expiry from (in order):
    1. close_time field
    2. expiration_time field
    3. Descriptor expiry token
    4. Ticker segments that look like dates
    5. timestamp field (last resort)

    Raises:
        RuntimeError: If no valid expiry can be derived
    """
    parser = token_parser if token_parser is not None else parse_expiry_token

    if descriptor_expiry_token:
        for candidate_token in (
            descriptor_expiry_token,
            descriptor_expiry_token.upper(),
            descriptor_expiry_token.strip(),
        ):
            direct_descriptor_dt = parser(candidate_token)
            if direct_descriptor_dt is not None:
                return _normalize_iso(direct_descriptor_dt.isoformat())

    # Try to get expiry from close_time or expiration_time fields
    expiry_from_metadata = _try_get_expiry_from_metadata(metadata)
    if expiry_from_metadata:
        return expiry_from_metadata

    # Try to parse expiry from ticker or descriptor
    candidate_segments = _collect_candidate_segments(market_ticker, descriptor_expiry_token)
    expiry_from_tokens = _try_parse_candidate_tokens(candidate_segments, parser)
    if expiry_from_tokens:
        return _normalize_iso(expiry_from_tokens)

    # Try to derive from timestamp as last resort
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    expiry_from_timestamp = _try_derive_from_timestamp(
        market_ticker, metadata.get("timestamp"), now_dt
    )
    if expiry_from_timestamp:
        return _normalize_iso(expiry_from_timestamp)

    raise DataError(
        f"Unable to derive expiry for {market_ticker}; metadata missing close_time and timestamp"
    )


def _try_get_expiry_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """Try to extract expiry from metadata fields."""
    raw_close_time = metadata.get("close_time") or metadata.get("expiration_time")
    if isinstance(raw_close_time, str) and raw_close_time:
        return raw_close_time
    return None


def _collect_candidate_segments(
    market_ticker: str, descriptor_expiry_token: Optional[str]
) -> List[str]:
    """Collect candidate segments from ticker and descriptor."""
    candidate_segments: List[str] = []

    if descriptor_expiry_token:
        candidate_segments.append(descriptor_expiry_token)

    parts = market_ticker.upper().split("-")
    for segment in parts[1:]:
        if any(char.isalpha() for char in segment):
            candidate_segments.append(segment)

    return candidate_segments


def _try_parse_candidate_tokens(
    candidate_segments: List[str], token_parser: Callable[..., Optional[datetime]]
) -> Optional[str]:
    """Try to parse expiry from candidate token segments."""
    for token in candidate_segments:
        candidate_dt = token_parser(token)
        if candidate_dt is not None:
            return candidate_dt.isoformat()
    return None


def _try_derive_from_timestamp(
    market_ticker: str, timestamp_value: Any, now_dt: datetime
) -> Optional[str]:
    """Try to derive expiry from timestamp field."""
    if timestamp_value in (None, ""):
        return None

    # Parse timestamp value
    try:
        seconds = float(timestamp_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Invalid timestamp value for {market_ticker}: {timestamp_value}"
        ) from exc

    # Validate timestamp is positive
    if seconds <= 0:
        raise RuntimeError(
            f"Timestamp for {market_ticker} must be positive (received {timestamp_value})"
        )

    # Convert to datetime and validate it's in the future
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    if dt <= now_dt:
        raise DataError(
            f"Timestamp-derived expiry for {market_ticker} is not in the future ({dt.isoformat()})"
        )

    return dt.isoformat()
