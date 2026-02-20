"""Trading price and algo constants.

These constants define the valid price ranges for Kalshi trading operations
and the canonical list of algorithm names used across the system.
"""

# Order price bounds (valid range for placing orders: 1-99 cents)
MIN_PRICE_CENTS = 1
MAX_PRICE_CENTS = 99

# Market display price bounds (markets can display 0-100 cents)
MIN_MARKET_PRICE_CENTS = 0
MAX_MARKET_PRICE_CENTS = 100

# Settlement price for binary markets (settles at 0 or 100)
MAX_SETTLEMENT_PRICE_CENTS = 100

# Canonical set of algorithm names recognized by the trading system.
# Single source of truth — producers and tracker both validate against this set.
# Update only here when adding a new algo.
VALID_ALGO_NAMES: frozenset[str] = frozenset({"crossarb", "peak", "edge", "weather", "pdf", "whale", "strike", "total", "dutch"})

__all__ = [
    "MIN_PRICE_CENTS",
    "MAX_PRICE_CENTS",
    "MIN_MARKET_PRICE_CENTS",
    "MAX_MARKET_PRICE_CENTS",
    "MAX_SETTLEMENT_PRICE_CENTS",
    "VALID_ALGO_NAMES",
]
