"""Ticker validation helpers for Kalshi markets."""

from typing import Any, Callable, Mapping, Optional

from src.common.redis_schema import is_supported_kalshi_ticker


def validate_ticker_support(
    metadata: Mapping[str, Any],
    checker: Callable[[str], bool] = is_supported_kalshi_ticker,
) -> tuple[bool, Optional[str]]:
    """Validate ticker is in supported category."""
    ticker_value = metadata.get("ticker") or metadata.get("market_ticker")
    if not ticker_value:
        return True, None  # No ticker to validate

    if not checker(str(ticker_value)):
        return False, "unsupported_category"

    return True, None
