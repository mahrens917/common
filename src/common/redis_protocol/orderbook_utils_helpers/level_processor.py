"""Level processing for orderbook snapshots."""

from typing import Any, Dict, List

from src.common.config_loader import load_config
from src.common.exceptions import DataError

VALIDATION_CONFIG = load_config("validation_constants.json")


class LevelProcessor:
    """Processes orderbook price levels for Redis storage."""

    @staticmethod
    def validate_price_level(price_level: Any, market_ticker: str) -> bool:
        """Validate a single price level structure."""
        if not (
            isinstance(price_level, (list, tuple))
            and len(price_level) == VALIDATION_CONFIG["field_counts"]["min_strike_components"]
        ):
            raise DataError(f"Corrupted order book data detected for market {market_ticker}")
        return True

    @staticmethod
    def is_valid_size(size: Any) -> bool:
        """Check if size is valid (numeric and positive)."""
        return isinstance(size, (int, float)) and size > 0

    @staticmethod
    def process_yes_level(
        price: Any, size: Any, orderbook_sides: Dict[str, Dict[str, float]]
    ) -> None:
        """Process a YES side price level."""
        orderbook_sides["yes_bids"][str(price)] = size

    @staticmethod
    def process_no_level(
        price: Any, size: Any, orderbook_sides: Dict[str, Dict[str, float]]
    ) -> None:
        """Process a NO side price level (convert to YES ask)."""
        converted_price = 100 - float(price)
        orderbook_sides["yes_asks"][str(converted_price)] = size

    @staticmethod
    def process_side_levels(
        side: str,
        levels: List[Any],
        market_ticker: str,
        orderbook_sides: Dict[str, Dict[str, float]],
    ) -> None:
        """Process all levels for a given side."""
        for price_level in levels:
            LevelProcessor.validate_price_level(price_level, market_ticker)
            price, size = price_level

            if not LevelProcessor.is_valid_size(size):
                continue

            if side == "yes":
                LevelProcessor.process_yes_level(price, size, orderbook_sides)
            else:
                LevelProcessor.process_no_level(price, size, orderbook_sides)
