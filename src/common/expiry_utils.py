"""
Expiry Utilities for Market Data Processing

Provides shared functionality for grouping markets by expiry dates across different phases.
Ensures consistent expiry calculation and grouping logic throughout the pipeline.

Business Purpose:
- Eliminate code duplication between Phase 6 and Phase 7
- Ensure consistent time-to-expiry calculations
- Provide proper market grouping by actual expiry dates
- Maintain data integrity with fail-fast error handling
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Union

from dateutil import parser

from common.exceptions import InvalidMarketDataError, ValidationError

logger = logging.getLogger(__name__)


def _resolve_market_ticker(market: Any) -> str:
    """Return a readable ticker identifier for logging."""
    ticker = getattr(market, "ticker", None)
    if ticker:
        return str(ticker)
    if isinstance(market, dict):
        dict_ticker = market.get("ticker")
        if dict_ticker:
            return str(dict_ticker)
    return "unknown"


def _extract_market_expiry_value(market_data: Union[Dict[str, Any], Any]) -> datetime:
    """Return the expiry datetime from either dict-based or object market payloads."""
    if hasattr(market_data, "expiry_time"):
        expiry_value = getattr(market_data, "expiry_time")
    elif isinstance(market_data, dict):
        expiry_value = (
            market_data.get("close_time")
            or market_data.get("expiry")
            or market_data.get("expiration_time")
        )
    else:
        expiry_value = None

    if not expiry_value:
        raise InvalidMarketDataError("No expiry field found in market data")

    if isinstance(expiry_value, str):
        expiry_value = parser.parse(expiry_value)

    if not isinstance(expiry_value, datetime):
        raise TypeError("Expiry value must resolve to a datetime instance")

    return expiry_value


def _ensure_timezone_awareness(dt: datetime) -> datetime:
    """Convert naive datetimes to UTC for consistent comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _compute_time_to_expiry_years(expiry_time: datetime, current_time: datetime) -> float:
    """
    Return the difference between two datetimes expressed in years.

    Delegates to canonical implementation in common.time_helpers.expiry_conversions.
    Note: parameter order is reversed compared to canonical (expiry first, current second).
    """
    from common.time_helpers.expiry_conversions import (
        calculate_time_to_expiry_years as _calculate_canonical,
    )

    return _calculate_canonical(current_time, expiry_time)


def calculate_time_to_expiry_from_market_data(
    market_data: Union[Dict[str, Any], Any], current_time: datetime
) -> float:
    """
    Calculate time to expiry in years from market data using authoritative expiry fields.

    Uses the same logic as Phase 7 for consistency across the pipeline.
    Handles both Kalshi market data (close_time) and enhanced market objects (expiry_time).

    Args:
        market_data: Market data dictionary or enhanced market object
        current_time: Reference time for calculation (should be program start time)

    Returns:
        Time to expiry in years (float)

    Raises:
        Exception: If expiry calculation fails (fail-fast principle)
    """
    try:
        market_expiry = _extract_market_expiry_value(market_data)
        time_to_expiry_years = _compute_time_to_expiry_years(
            _ensure_timezone_awareness(market_expiry),
            _ensure_timezone_awareness(current_time),
        )
        return max(0.0, time_to_expiry_years)
    except (ValueError, TypeError, OverflowError) as e:
        ticker = _resolve_market_ticker(market_data)
        raise InvalidMarketDataError(
            f"Time to expiry calculation failed for market {ticker}"
        ) from e


def group_markets_by_expiry(
    markets: List[Any], current_time: datetime, use_time_buckets: bool = False
) -> Dict[float, List[Any]]:
    """
    Group markets by their expiry dates using consistent time-to-expiry calculations.

    This function provides the CORRECT expiry grouping logic that should be used
    across all phases, replacing the broken single-expiry-group logic in Phase 6.

    Args:
        markets: List of market data (dicts or enhanced market objects)
        current_time: Reference time for calculations (program start time)
        use_time_buckets: If True, group into time buckets like Phase 7; if False, use exact expiry times

    Returns:
        Dictionary mapping time_to_expiry (float) to list of markets

    Raises:
        Exception: If grouping fails (fail-fast principle)
    """
    if not markets:
        raise InvalidMarketDataError("Cannot group empty market list")

    markets_by_expiry = {}
    skipped_markets = 0

    for market in markets:
        try:
            # Calculate time to expiry for this market
            time_to_expiry_years = calculate_time_to_expiry_from_market_data(market, current_time)

            # Skip expired markets
            if time_to_expiry_years <= 0:
                skipped_markets += 1
                continue

            # Determine grouping key
            if use_time_buckets:
                # Use Phase 7 style time buckets (0, 1, 2) for compatibility
                expiry_index = min(2, max(0, int(time_to_expiry_years * 2)))
                expiry_key = float(expiry_index)
            else:
                # Use exact time to expiry for Phase 6 style processing
                # Round to avoid floating point precision issues
                expiry_key = round(time_to_expiry_years, 6)

            # Group markets by expiry
            if expiry_key not in markets_by_expiry:
                markets_by_expiry[expiry_key] = []
            markets_by_expiry[expiry_key].append(market)

        except (ValueError, TypeError, OverflowError):
            ticker = _resolve_market_ticker(market)
            logger.warning(f"Failed to process market {ticker} for expiry grouping")
            skipped_markets += 1
            continue

    if not markets_by_expiry:
        raise ValueError(
            f"No valid markets found after expiry grouping. Skipped {skipped_markets} markets."
        )

    logger.info(
        f"Grouped {len(markets)} markets into {len(markets_by_expiry)} expiry groups. Skipped {skipped_markets} expired markets."
    )

    # Log expiry group details for debugging
    for expiry_key, expiry_markets in markets_by_expiry.items():
        logger.debug(f"Expiry group {expiry_key}: {len(expiry_markets)} markets")

    return markets_by_expiry


def validate_expiry_group_strikes(
    expiry_groups: Dict[float, List[Any]], minimum_strikes: int
) -> Dict[float, List[Any]]:
    """
    Validate that each expiry group has sufficient strikes for processing.

    Filters out expiry groups that don't meet the minimum strike requirement.
    This prevents the "Insufficient strikes" error that was causing test failures.

    Args:
        expiry_groups: Dictionary mapping expiry to list of markets
        minimum_strikes: Minimum number of unique strikes required per expiry

    Returns:
        Filtered dictionary with only valid expiry groups

    Raises:
        Exception: If no valid expiry groups remain after filtering
    """
    valid_expiry_groups = {}

    for expiry_key, markets in expiry_groups.items():
        unique_strikes = _extract_unique_strikes_from_markets(markets)

        if len(unique_strikes) >= minimum_strikes:
            valid_expiry_groups[expiry_key] = markets
            logger.debug(f"Expiry group {expiry_key}: {len(unique_strikes)} unique strikes (valid)")
        else:
            logger.warning(
                f"Expiry group {expiry_key}: {len(unique_strikes)} unique strikes < {minimum_strikes} (filtered out)"
            )

    if not valid_expiry_groups:
        raise ValidationError(
            f"No expiry groups have sufficient strikes (minimum {minimum_strikes} required)"
        )

    logger.info(
        f"Validated expiry groups: {len(valid_expiry_groups)}/{len(expiry_groups)} groups have sufficient strikes"
    )

    return valid_expiry_groups


def _extract_unique_strikes_from_markets(markets: List[Any]) -> List[float]:
    """Extract unique strike values from a list of markets."""
    strikes = []
    for market in markets:
        try:
            market_strikes = _extract_strikes_from_market(market)
            strikes.extend(market_strikes)
        except (ValueError, TypeError):
            ticker = _resolve_market_ticker(market)
            logger.warning(f"Failed to extract strikes from market {ticker}")
            continue

    return list(set(strikes))


def _extract_strikes_from_market(market: Any) -> List[float]:
    """Extract available strike values from either dict or dataclass markets."""
    strikes: List[float] = []

    for field in ("strike", "floor_strike", "cap_strike"):
        value = _get_field_value(market, field)

        if value in (None, ""):
            continue

        try:
            strikes.append(float(value))
        except (TypeError, ValueError):
            logger.warning("Invalid strike value '%s' for field %s", value, field)

    return strikes


def _get_field_value(market: Any, field: str) -> Any:
    """Get field value from market (supports both dict and object)."""
    if hasattr(market, field):
        return getattr(market, field)
    if isinstance(market, dict):
        return market.get(field)
    return None
