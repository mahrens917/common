"""Market ownership detection and validation."""

from typing import Any, Dict, Optional

# Weather prefixes
_WEATHER_PREFIXES = ("KXHIGH", "KXLOW")

# PDF prefixes (crypto markets)
_PDF_PREFIXES = ("KXBTC", "KXETH")


def _is_mutually_exclusive(market_data: Optional[Dict[str, Any]]) -> bool:
    """Check if market has mutually_exclusive=True."""
    if not market_data:
        return True  # Assume ME if no data provided
    me_value = market_data.get("mutually_exclusive")
    return me_value in (True, "true", "True")


def get_required_owner(ticker: str, market_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Return the algo that must own this market type, or None if any algo can claim.

    Args:
        ticker: Market ticker (e.g., "KXHIGHNY-25DEC28-T44", "KXBTCD-25JAN28-T100000")
        market_data: Optional market data dict to check mutually_exclusive flag

    Returns:
        "weather" for weather markets, "pdf" for PDF markets, None otherwise
    """
    ticker_upper = ticker.upper()

    # Weather markets: KXHIGH* or KXLOW* with mutually_exclusive=True
    if any(ticker_upper.startswith(prefix) for prefix in _WEATHER_PREFIXES):
        if _is_mutually_exclusive(market_data):
            return "weather"

    # PDF markets: KXBTC* or KXETH* with mutually_exclusive=True
    if any(ticker_upper.startswith(prefix) for prefix in _PDF_PREFIXES):
        if _is_mutually_exclusive(market_data):
            return "pdf"

    return None


def can_algo_own_market(
    algo: str,
    ticker: str,
    current_owner: Optional[str] = None,
    market_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Check if algo can claim ownership of market.

    Args:
        algo: Algorithm name (e.g., "peak", "weather", "pdf")
        ticker: Market ticker
        current_owner: Current market owner from Redis, if any
        market_data: Optional market data dict for additional checks

    Returns:
        True if algo can own this market
    """
    required = get_required_owner(ticker, market_data)

    # Market type constraint: only specific algo can own
    if required and algo != required:
        return False

    # Speed rule: first algo wins, same algo can update
    if current_owner and current_owner != algo:
        return False

    return True


__all__ = ["can_algo_own_market", "get_required_owner"]
