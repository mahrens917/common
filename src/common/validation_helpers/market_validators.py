"""Market-specific validation helpers.

Delegates price validation to canonical src/common/validation/kalshi_price_validator.
"""

from common.validation.kalshi_price_validator import (
    validate_kalshi_bid_ask_relationship,
)

from .exceptions import ValidationError


class MarketValidators:
    """Validators for market data and trading operations."""

    @staticmethod
    def derive_strike_price_bounds_from_market_data(options_data):
        """Derive strike price bounds from actual market data analysis. Returns: Tuple of (min_strike, max_strike) derived from real market data"""
        if not options_data:
            raise ValidationError("No options data provided for strike price bounds derivation")
        valid_strikes = []
        for option in options_data:
            if hasattr(option, "strike") and option.strike is not None and option.strike > 0:
                valid_strikes.append(option.strike)
        if not valid_strikes:
            raise ValidationError("No valid strike prices found in market data for bounds derivation")
        market_min_strike = min(valid_strikes)
        market_max_strike = max(valid_strikes)
        safety_margin_low = 0.5
        safety_margin_high = 2.0
        min_strike = market_min_strike * safety_margin_low
        max_strike = market_max_strike * safety_margin_high
        return min_strike, max_strike

    @staticmethod
    def validate_bid_ask_relationship(bid: float, ask: float, instrument_name: str = "instrument") -> bool:
        """Validate bid <= ask relationship for market data.

        Delegates to canonical validate_kalshi_bid_ask_relationship.
        """
        from .numerical_validators import NumericalValidators

        NumericalValidators.validate_market_price(bid, f"{instrument_name} bid")
        NumericalValidators.validate_market_price(ask, f"{instrument_name} ask")
        validate_kalshi_bid_ask_relationship(bid, ask)
        return True

    @staticmethod
    def validate_volume_and_open_interest(volume: int, open_interest: int) -> bool:
        """Validate volume and open interest are non-negative integers."""
        try:
            volume_check = volume < 0
        except TypeError:
            raise ValidationError(f"Volume must be integer, got {type(volume).__name__}")
        if volume_check:
            raise ValidationError(f"Volume {volume} cannot be negative")
        try:
            open_interest_check = open_interest < 0
        except TypeError:
            raise ValidationError(f"Open interest must be integer, got {type(open_interest).__name__}")
        if open_interest_check:
            raise ValidationError(f"Open interest {open_interest} cannot be negative")
        return True
