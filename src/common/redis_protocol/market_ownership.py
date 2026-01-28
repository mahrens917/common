"""Market ownership detection and validation."""

from typing import Any, Dict, Optional

# Weather prefixes
_WEATHER_PREFIXES = ("KXHIGH", "KXLOW")

# PDF prefixes (crypto markets)
_PDF_PREFIXES = ("KXBTC", "KXETH")


def _is_mutually_exclusive(market_data: Optional[Dict[str, Any]]) -> bool:
    """Check if market has mutually_exclusive=True.

    Defaults to True (assume ME) when:
    - market_data is None/empty
    - mutually_exclusive field is missing or None

    Only returns False when mutually_exclusive is explicitly False.
    """
    if not market_data:
        return True  # Assume ME if no data provided
    me_value = market_data.get("mutually_exclusive")
    if me_value is None:
        return True  # Assume ME if field is missing
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


def can_algo_own_market_type(
    algo: str,
    ticker: str,
    market_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Check if algo is allowed to own this market type.

    Only checks market type restrictions (weather/PDF).
    Does NOT check current ownership - ownership is now dynamic
    and re-evaluated on every price change based on tradeable edge.

    Args:
        algo: Algorithm name (e.g., "peak", "weather", "pdf")
        ticker: Market ticker
        market_data: Optional market data dict for additional checks

    Returns:
        True if algo is allowed to own this market type
    """
    required = get_required_owner(ticker, market_data)

    # Market type constraint: only specific algo can own
    if required and algo != required:
        return False

    return True


def can_algo_own_market(
    algo: str,
    ticker: str,
    current_owner: Optional[str] = None,
    market_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Check if algo can claim ownership of market.

    DEPRECATED: Use can_algo_own_market_type() instead.
    This function is kept for backward compatibility but the
    current_owner check is no longer used (ownership is dynamic).

    Args:
        algo: Algorithm name (e.g., "peak", "weather", "pdf")
        ticker: Market ticker
        current_owner: Ignored (kept for backward compatibility)
        market_data: Optional market data dict for additional checks

    Returns:
        True if algo can own this market
    """
    del current_owner  # No longer used - ownership is dynamic
    return can_algo_own_market_type(algo, ticker, market_data)


__all__ = ["can_algo_own_market", "can_algo_own_market_type", "get_required_owner"]
