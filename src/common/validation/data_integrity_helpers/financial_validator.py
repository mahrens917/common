"""Financial data validation for data integrity checks."""

import logging
from typing import Tuple

from ..data_integrity_validator import DataIntegrityError
from .numeric_validator import NumericValidator

logger = logging.getLogger(__name__)


class FinancialValidator:
    """Validator for financial data (options, strikes, prices, etc.)."""

    @staticmethod
    def validate_expiry_value(expiry: object, variable_name: str = "expiry") -> float:
        validated_expiry = NumericValidator.validate_numeric_value(
            expiry,
            variable_name,
            allow_zero=False,
            allow_negative=False,
            min_value=1e-6,
            max_value=10.0,
        )
        return validated_expiry

    @staticmethod
    def validate_strike_price(strike: object, variable_name: str = "strike_price") -> float:
        validated_strike = NumericValidator.validate_numeric_value(
            strike,
            variable_name,
            allow_zero=False,
            allow_negative=False,
            min_value=0.01,
            max_value=1e9,
        )
        return validated_strike

    @staticmethod
    def validate_option_price(price: object, variable_name: str = "option_price") -> float:
        validated_price = NumericValidator.validate_numeric_value(
            price,
            variable_name,
            allow_zero=True,
            allow_negative=False,
            min_value=0.0,
            max_value=1e9,
        )
        return validated_price

    @staticmethod
    def validate_bid_ask_prices(
        bid_price: object, ask_price: object, variable_prefix: str = "price"
    ) -> Tuple[float, float]:
        validated_bid = FinancialValidator.validate_option_price(
            bid_price, f"{variable_prefix}_bid"
        )
        validated_ask = FinancialValidator.validate_option_price(
            ask_price, f"{variable_prefix}_ask"
        )

        if validated_bid > validated_ask:
            raise DataIntegrityError(
                f"Bid-ask crossing detected: {variable_prefix}_bid ({validated_bid}) > {variable_prefix}_ask ({validated_ask})"
            )

        return validated_bid, validated_ask
