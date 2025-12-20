"""Crypto market detection logic."""

from typing import Dict

from .crypto_market_checker import is_crypto_market as check_crypto_market


class CryptoMarketDetector:
    """Detects and validates crypto-related markets."""

    def is_crypto_market(self, market: Dict[str, object]) -> bool:
        """Check if market is crypto-related by scanning fields."""
        return check_crypto_market(market)
