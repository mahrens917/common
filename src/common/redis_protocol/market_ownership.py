"""Market ownership detection and validation."""

from typing import Any, Dict, List, Optional

_config: Optional[Dict[str, Any]] = None


def configure_ownership(config: Dict[str, Any]) -> None:
    """Store ownership config. Called once at tracker startup."""
    global _config
    _config = config


def _get_config() -> Dict[str, Any]:
    """Return stored config or raise if not configured."""
    if _config is None:
        raise RuntimeError("market_ownership not configured: call configure_ownership() first")
    return _config


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
    return me_value is None or me_value in (True, "true", "True")


def get_required_owner(ticker: str, market_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Return the algo that must own this market type, or None if any algo can claim.

    Args:
        ticker: Market ticker (e.g., "KXHIGHNY-25DEC28-T44", "KXBTCD-25JAN28-T100000")
        market_data: Optional market data dict to check mutually_exclusive flag

    Returns:
        Required owner algo name, or None if unrestricted
    """
    config = _get_config()
    ticker_upper = ticker.upper()

    restrictions: List[Dict[str, Any]] = config["market_type_restrictions"]
    for restriction in restrictions:
        prefixes: List[str] = restriction["prefixes"]
        if any(ticker_upper.startswith(prefix) for prefix in prefixes):
            if restriction["require_mutually_exclusive"] and _is_mutually_exclusive(market_data):
                return restriction["owner"]
            if not restriction["require_mutually_exclusive"]:
                return restriction["owner"]

    return None


def can_algo_own_market_type(
    algo: str,
    ticker: str,
    market_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Check if algo is allowed to own this market type.

    Only checks market type restrictions.
    Does NOT check current ownership - ownership is now dynamic
    and re-evaluated on every price change based on tradeable edge.

    Args:
        algo: Algorithm name (e.g., "peak", "weather", "pdf")
        ticker: Market ticker
        market_data: Optional market data dict for additional checks

    Returns:
        True if algo is allowed to own this market type
    """
    config = _get_config()

    if algo in config["unrestricted_algos"]:
        return True

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

    Args:
        algo: Algorithm name (e.g., "peak", "weather", "pdf")
        ticker: Market ticker
        current_owner: Ignored (kept for external callers)
        market_data: Optional market data dict for additional checks

    Returns:
        True if algo can own this market
    """
    del current_owner  # No longer used - ownership is dynamic
    return can_algo_own_market_type(algo, ticker, market_data)


__all__ = ["can_algo_own_market", "can_algo_own_market_type", "configure_ownership", "get_required_owner"]
