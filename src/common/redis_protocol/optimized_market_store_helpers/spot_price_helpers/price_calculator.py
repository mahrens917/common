"""Price calculation and validation"""

import logging
from typing import Any, Dict

from common.exceptions import DataError, ValidationError

logger = logging.getLogger(__name__)


class PriceCalculator:
    """Calculates and validates spot prices from market data"""

    @staticmethod
    def calculate_spot_price(market_data: Dict[str, Any], currency: str) -> float:
        """
        Calculate spot price from market bid/ask data

        Args:
            market_data: Market data dictionary containing best_bid and best_ask
            currency: Currency symbol for logging

        Returns:
            Spot price calculated as mid-price between bid and ask

        Raises:
            ValueError: If market data is invalid or missing required fields
        """
        # Fail fast - no default values allowed for market data
        best_bid_str = market_data.get("best_bid")
        best_ask_str = market_data.get("best_ask")

        if best_bid_str is None or best_ask_str is None:
            raise ValidationError("Missing required 'best_bid' or 'best_ask' fields in market data - no default values allowed")

        best_bid = float(best_bid_str)
        best_ask = float(best_ask_str)

        if best_bid <= 0 or best_ask <= 0:
            raise ValidationError(f"Invalid market prices: bid={best_bid}, ask={best_ask}. Must be positive.")

        if best_ask <= best_bid:
            raise ValidationError(f"Invalid market spread: bid={best_bid} >= ask={best_ask}. Ask must be greater than bid.")

        # Calculate spot price as mid-price between bid and ask
        spot_price = (best_bid + best_ask) / 2.0

        logger.debug(
            "Retrieved Deribit spot price for %s: %s (bid=%s, ask=%s)",
            currency,
            spot_price,
            best_bid,
            best_ask,
        )
        return spot_price

    @staticmethod
    def extract_bid_ask_prices(market_data: Dict[str, Any], currency: str) -> tuple[float, float]:
        """
        Extract and parse bid/ask prices from market data

        Args:
            market_data: Market data dictionary
            currency: Currency symbol for error messages

        Returns:
            Tuple of (bid_price, ask_price)

        Raises:
            ValueError: If data is missing or invalid
        """
        best_bid_str = market_data.get("best_bid")
        best_ask_str = market_data.get("best_ask")
        if best_bid_str is None or best_ask_str is None:
            raise DataError(f"USDC pair market data incomplete for {currency}; bid='{best_bid_str}', ask='{best_ask_str}'")

        try:
            bid_price = float(best_bid_str)
            ask_price = float(best_ask_str)
        except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
            raise ValidationError(f"USDC pair market data invalid for {currency}; bid='{best_bid_str}', ask='{best_ask_str}'") from exc

        return bid_price, ask_price
