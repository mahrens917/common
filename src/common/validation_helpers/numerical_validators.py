"""Numerical validation helpers."""

import math

from common.validation.data_integrity_validator import (
    DataIntegrityError,
    DataIntegrityValidator,
)

_common_validate_strike_price = DataIntegrityValidator.validate_strike_price

from .exceptions import ValidationError

KALSHI_MAX_PRICE_CENTS = 100.0


class NumericalValidators:
    """Validators for numerical values."""

    @staticmethod
    def validate_probability_value(probability: float) -> bool:
        """Validate probability value is within [0, 1] range and not NaN/inf."""
        try:
            is_nan = math.isnan(probability)
        except TypeError:
            raise TypeError(f"probability must be numeric, got {type(probability).__name__}")
        if is_nan:
            raise ValidationError("Probability cannot be NaN")
        try:
            is_inf = math.isinf(probability)
        except TypeError:
            raise TypeError(f"probability must be numeric, got {type(probability).__name__}")
        if is_inf:
            raise ValidationError("Probability cannot be infinite")
        if probability < 0.0 or probability > 1.0:
            raise ValidationError(f"Probability {probability} must be in range [0, 1]")
        return True

    @staticmethod
    def validate_strike_price(strike_price: float) -> bool:
        """Validate strike price is positive and within reasonable bounds."""
        try:
            _common_validate_strike_price(strike_price)
        except DataIntegrityError as exc:
            raise ValidationError(str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise TypeError(f"Strike price must be numeric, got {type(strike_price)}") from exc
        return True

    @staticmethod
    def validate_market_price(price: float, price_type: str = "market") -> bool:
        """Validate market price is non-negative and within reasonable bounds."""
        try:
            is_nan = math.isnan(price)
        except TypeError:
            raise TypeError(f"price must be numeric, got {type(price).__name__}")
        if is_nan:
            raise ValidationError(f"{price_type} price cannot be NaN")
        try:
            is_inf = math.isinf(price)
        except TypeError:
            raise TypeError(f"price must be numeric, got {type(price).__name__}")
        if is_inf:
            raise ValidationError(f"{price_type} price cannot be infinite")
        if price < 0:
            raise ValidationError(f"{price_type} price {price} cannot be negative")
        if price_type.lower() in ["kalshi", "yes", "no"] and price > KALSHI_MAX_PRICE_CENTS:
            raise ValidationError(f"{price_type} price {price} exceeds maximum of {KALSHI_MAX_PRICE_CENTS} cents")
        return True

    @staticmethod
    def validate_numerical_range(value: float, min_value: float, max_value: float, value_name: str = "value") -> bool:
        """Validate numerical value is within specified range."""
        try:
            is_nan = math.isnan(value)
        except TypeError:
            raise TypeError(f"{value_name} must be numeric, got {type(value).__name__}")
        if is_nan:
            raise ValidationError(f"{value_name} cannot be NaN")
        try:
            is_inf = math.isinf(value)
        except TypeError:
            raise TypeError(f"{value_name} must be numeric, got {type(value).__name__}")
        if is_inf:
            raise ValidationError(f"{value_name} cannot be infinite")
        if value < min_value or value > max_value:
            raise ValidationError(f"{value_name} {value} must be in range [{min_value}, {max_value}]")
        return True
