"""Slim coordinator for micro price validation.

Delegates validation logic to focused helper modules.
"""

from typing import List

from .calculation_validator import CalculationValidator
from .constraint_validator import ConstraintValidator
from .error_collector import ErrorCollector
from .field_validator import FieldValidator
from .relationship_validator import RelationshipValidator
from .validation_params import (
    BasicOptionData,
    MathematicalRelationships,
    ValidationErrorParams,
)


def validate_basic_option_data(params: BasicOptionData) -> None:
    """Validate basic option data constraints."""
    FieldValidator.validate_basic_option_data(params)


def validate_micro_price_calculations(
    absolute_spread: float,
    i_raw: float,
    p_raw: float,
) -> None:
    """Validate micro price calculation constraints."""
    CalculationValidator.validate_micro_price_calculations(
        absolute_spread=absolute_spread,
        i_raw=i_raw,
        p_raw=p_raw,
    )


def validate_mathematical_relationships(params: MathematicalRelationships) -> None:
    """Validate mathematical relationships between variables."""
    RelationshipValidator.validate_spread_relationship(
        params.best_bid, params.best_ask, params.absolute_spread
    )
    RelationshipValidator.validate_relative_spread(
        params.absolute_spread, params.relative_spread, params.p_raw
    )
    RelationshipValidator.validate_intensity_calculation(
        params.best_bid_size, params.best_ask_size, params.i_raw
    )
    RelationshipValidator.validate_micro_price_calculation(
        params.best_bid, params.best_ask, params.best_bid_size, params.best_ask_size, params.p_raw
    )
    RelationshipValidator.validate_g_transformation(params.absolute_spread, params.g)
    RelationshipValidator.validate_h_transformation(params.i_raw, params.h)


def validate_micro_price_constraints(
    best_bid: float,
    best_ask: float,
    absolute_spread: float,
    i_raw: float,
    p_raw: float,
) -> bool:
    """Validate that micro price calculations satisfy mathematical constraints."""
    return ConstraintValidator.validate_micro_price_constraints(
        best_bid=best_bid,
        best_ask=best_ask,
        absolute_spread=absolute_spread,
        i_raw=i_raw,
        p_raw=p_raw,
    )


def get_validation_errors(params: ValidationErrorParams) -> List[str]:
    """Get list of validation errors for micro price data."""
    return ErrorCollector.get_validation_errors(params)


class MicroPriceValidator:
    """Slim coordinator for micro price validation."""

    NUMERICAL_TOLERANCE = RelationshipValidator.NUMERICAL_TOLERANCE
    validate_basic_option_data = staticmethod(validate_basic_option_data)
    validate_micro_price_calculations = staticmethod(validate_micro_price_calculations)
    validate_mathematical_relationships = staticmethod(validate_mathematical_relationships)
    validate_micro_price_constraints = staticmethod(validate_micro_price_constraints)
    get_validation_errors = staticmethod(get_validation_errors)
