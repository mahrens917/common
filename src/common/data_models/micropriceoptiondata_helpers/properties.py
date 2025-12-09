"""Property methods and computed attributes for MicroPriceOptionData."""

from datetime import datetime


class MicroPriceProperties:
    """Provides property methods for MicroPriceOptionData instances."""

    @staticmethod
    def get_is_future() -> bool:
        """Always False for options (compatibility property)."""
        return False

    @staticmethod
    def get_expiry_timestamp(expiry: datetime) -> int:
        """Expiry as Unix timestamp (compatibility property)."""
        return int(expiry.timestamp())

    @staticmethod
    def get_bid_price(best_bid: float) -> float:
        """Alias for best_bid (compatibility property)."""
        return best_bid

    @staticmethod
    def get_ask_price(best_ask: float) -> float:
        """Alias for best_ask (compatibility property)."""
        return best_ask

    @staticmethod
    def get_mid_price(best_bid: float, best_ask: float) -> float:
        """Average of bid and ask."""
        return (best_bid + best_ask) / 2.0

    @staticmethod
    def get_spread(absolute_spread: float) -> float:
        """Alias for absolute_spread."""
        return absolute_spread

    @staticmethod
    def check_is_call(option_type: str) -> bool:
        """Check if this is a call option."""
        return option_type.lower() == "call"

    @staticmethod
    def check_is_put(option_type: str) -> bool:
        """Check if this is a put option."""
        return option_type.lower() == "put"
