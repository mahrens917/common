"""Expiration checking logic for market cleanup."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def is_expired_kalshi(expiration_time_str: str, grace_period_days: int) -> bool:
    """
    Check if Kalshi market is expired beyond grace period.

    Args:
        expiration_time_str: ISO8601 expiration timestamp
        grace_period_days: Days after expiration to keep markets

    Returns:
        True if expired beyond grace period
    """
    try:
        expiration_time = datetime.fromisoformat(expiration_time_str.replace("Z", "+00:00"))

        if expiration_time.tzinfo is None:
            expiration_time = expiration_time.replace(tzinfo=timezone.utc)

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=grace_period_days)
    except (ValueError, AttributeError) as exc:  # policy_guard: allow-silent-handler
        logger.warning(
            "Failed to parse Kalshi expiration time '%s': %s",
            expiration_time_str,
            exc,
        )
        return False
    else:
        return expiration_time < cutoff_time


def is_expired_deribit(expiry_str: str, grace_period_days: int) -> bool:
    """
    Check if Deribit option is expired beyond grace period.

    Args:
        expiry_str: Expiry date in YYYY-MM-DD format
        grace_period_days: Days after expiration to keep markets

    Returns:
        True if expired beyond grace period
    """
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=grace_period_days)
    except (ValueError, AttributeError) as exc:  # policy_guard: allow-silent-handler
        logger.warning(
            "Failed to parse Deribit expiry date '%s': %s",
            expiry_str,
            exc,
        )
        return False
    else:
        return expiry_date < cutoff_time


def extract_expiration_time(market_data: dict) -> Optional[str]:
    """Extract expiration time string from market data."""
    expiration_time_raw = market_data.get(b"latest_expiration_time")
    if expiration_time_raw is None:
        expiration_time_raw = market_data.get("latest_expiration_time")

    if not expiration_time_raw:
        return None

    return expiration_time_raw.decode() if isinstance(expiration_time_raw, bytes) else str(expiration_time_raw)
