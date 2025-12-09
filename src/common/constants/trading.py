"""Trading price constants.

These constants define the valid price ranges for Kalshi trading operations.
"""

# Order price bounds (valid range for placing orders: 1-99 cents)
MIN_PRICE_CENTS = 1
MAX_PRICE_CENTS = 99

# Market display price bounds (markets can display 0-100 cents)
MIN_MARKET_PRICE_CENTS = 0
MAX_MARKET_PRICE_CENTS = 100

# Settlement price for binary markets (settles at 0 or 100)
MAX_SETTLEMENT_PRICE_CENTS = 100

__all__ = [
    "MIN_PRICE_CENTS",
    "MAX_PRICE_CENTS",
    "MIN_MARKET_PRICE_CENTS",
    "MAX_MARKET_PRICE_CENTS",
    "MAX_SETTLEMENT_PRICE_CENTS",
]
