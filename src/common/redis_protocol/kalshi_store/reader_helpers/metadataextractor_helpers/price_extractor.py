"""
Price Extractor - Extract best bid/ask prices from metadata

Coerces price values to floats with error handling.
"""

from typing import Any, Dict, Optional


class PriceExtractor:
    """Extract market prices from metadata"""

    @staticmethod
    def extract_market_prices(metadata: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
        """
        Extract best bid and ask prices from metadata

        Args:
            metadata: Market metadata dict

        Returns:
            Tuple of (best_bid, best_ask) or None values
        """

        def _coerce(value: Any) -> Optional[float]:
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (  # policy_guard: allow-silent-handler
                TypeError,
                ValueError,
            ):
                return None

        return _coerce(metadata.get("yes_bid")), _coerce(metadata.get("yes_ask"))
