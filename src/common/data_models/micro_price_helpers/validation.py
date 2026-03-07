"""Slim coordinator for micro price validation.

Delegates validation logic to focused helper modules.
"""

from .calculation_validator import validate_micro_price_calculations as _validate_calcs
from .error_collector import get_validation_errors
from .field_validator import validate_basic_option_data as _validate_basic
from .relationship_validator import (
    NUMERICAL_TOLERANCE,
    validate_g_transformation,
    validate_h_transformation,
    validate_intensity_calculation,
    validate_micro_price_calculation,
    validate_relative_spread,
    validate_spread_relationship,
)
from .validation_params import (
    BasicOptionData,
    MathematicalRelationships,
)


def validate_basic_option_data(params: BasicOptionData) -> None:
    """Validate basic option data constraints."""
    _validate_basic(params)


def validate_micro_price_calculations(
    absolute_spread: float,
    i_raw: float,
    p_raw: float,
) -> None:
    """Validate micro price calculation constraints."""
    _validate_calcs(
        absolute_spread=absolute_spread,
        i_raw=i_raw,
        p_raw=p_raw,
    )


def validate_mathematical_relationships(params: MathematicalRelationships) -> None:
    """Validate mathematical relationships between variables."""
    validate_spread_relationship(params.best_bid, params.best_ask, params.absolute_spread)
    validate_relative_spread(params.absolute_spread, params.relative_spread, params.p_raw)
    validate_intensity_calculation(params.best_bid_size, params.best_ask_size, params.i_raw)
    validate_micro_price_calculation(params.best_bid, params.best_ask, params.best_bid_size, params.best_ask_size, params.p_raw)
    validate_g_transformation(params.absolute_spread, params.g)
    validate_h_transformation(params.i_raw, params.h)
