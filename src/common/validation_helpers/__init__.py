"""Validation helper modules."""

from datetime import datetime
from typing import Any, Dict, List, Union

from .datetime_validators import DatetimeValidators
from .exceptions import ValidationError
from .format_validators import FormatValidators
from .market_validators import MarketValidators
from .numerical_validators import NumericalValidators
from .structure_validators import StructureValidators


class ValidationHelpers:
    """Centralized validation utilities for PDF module data integrity. Provides comprehensive validation functions for numerical data, datetime objects, market data structures, and business rules."""

    @staticmethod
    def _derive_strike_price_bounds_from_market_data(options_data):
        """Derive strike price bounds from actual market data analysis."""
        return MarketValidators.derive_strike_price_bounds_from_market_data(options_data)

    @staticmethod
    def validate_probability_value(probability: float) -> bool:
        """Validate probability value is within [0, 1] range and not NaN/inf."""
        return NumericalValidators.validate_probability_value(probability)

    @staticmethod
    def validate_strike_price(strike_price: float) -> bool:
        """Validate strike price is positive and within reasonable bounds."""
        return NumericalValidators.validate_strike_price(strike_price)

    @staticmethod
    def validate_market_price(price: float, price_type: str = "market") -> bool:
        """Validate market price is non-negative and within reasonable bounds."""
        return NumericalValidators.validate_market_price(price, price_type)

    @staticmethod
    def validate_datetime_object(dt: datetime, field_name: str = "datetime") -> bool:
        """Validate datetime object is valid and not None."""
        return DatetimeValidators.validate_datetime_object(dt, field_name)

    @staticmethod
    def validate_time_to_expiry(time_to_expiry: float) -> bool:
        """Validate time to expiry is positive and within reasonable bounds."""
        return DatetimeValidators.validate_time_to_expiry(time_to_expiry)

    @staticmethod
    def validate_bid_ask_relationship(
        bid: float, ask: float, instrument_name: str = "instrument"
    ) -> bool:
        """Validate bid <= ask relationship for market data."""
        return MarketValidators.validate_bid_ask_relationship(bid, ask, instrument_name)

    @staticmethod
    def validate_volume_and_open_interest(volume: int, open_interest: int) -> bool:
        """Validate volume and open interest are non-negative integers."""
        return MarketValidators.validate_volume_and_open_interest(volume, open_interest)

    @staticmethod
    def validate_currency_code(currency: str) -> bool:
        """Validate currency code is supported."""
        return FormatValidators.validate_currency_code(currency)

    @staticmethod
    def validate_ticker_format(ticker: str) -> bool:
        """Validate Kalshi ticker format contains required components."""
        return FormatValidators.validate_ticker_format(ticker)

    @staticmethod
    def validate_list_not_empty(data_list: List[Any], list_name: str = "list") -> bool:
        """Validate list is not None and not empty."""
        return StructureValidators.validate_list_not_empty(data_list, list_name)

    @staticmethod
    def validate_dictionary_has_keys(
        data_dict: Dict[str, Any], required_keys: List[str], dict_name: str = "dictionary"
    ) -> bool:
        """Validate dictionary contains all required keys."""
        return StructureValidators.validate_dictionary_has_keys(data_dict, required_keys, dict_name)

    @staticmethod
    def validate_numerical_range(
        value: Union[int, float],
        min_value: Union[int, float],
        max_value: Union[int, float],
        value_name: str = "value",
    ) -> bool:
        """Validate numerical value is within specified range."""
        return NumericalValidators.validate_numerical_range(value, min_value, max_value, value_name)


__all__ = [
    "DatetimeValidators",
    "FormatValidators",
    "MarketValidators",
    "NumericalValidators",
    "StructureValidators",
    "ValidationError",
    "ValidationHelpers",
]
