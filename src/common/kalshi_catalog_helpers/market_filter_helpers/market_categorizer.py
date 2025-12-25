"""Market categorization and validation helpers."""

from typing import Dict


def create_empty_stats() -> Dict[str, int]:
    """Create empty stats dictionary."""
    return {
        "crypto_total": 0,
        "crypto_kept": 0,
        "weather_total": 0,
        "weather_kept": 0,
        "other_total": 0,
    }


def is_valid_market(market: object) -> bool:
    """Check if market is valid and has a ticker."""
    if not isinstance(market, dict):
        return False
    ticker_val = market.get("ticker")
    if ticker_val:
        ticker = str(ticker_val)
    else:
        ticker = ""
    return bool(ticker)
