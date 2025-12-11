"""
Data Integrity Validator

Provides robust null checking and data validation for the PDF pipeline to prevent
the data type and null handling issues identified in test failures.

This module implements fail-fast validation with clear error messages to catch
data integrity issues at pipeline entry points before they propagate to
mathematical operations.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# Constants
_CONST_50 = 50


class DataIntegrityError(Exception):
    """
    Exception raised when data integrity validation fails.

    This exception provides clear error messages about what validation failed
    and where, enabling rapid diagnosis of data quality issues.
    """

    pass


class DataIntegrityValidator:
    """Comprehensive data integrity validator for the PDF pipeline."""

    @staticmethod
    def validate_numeric_value(
        value: Any,
        variable_name: str,
        allow_zero: bool = True,
        allow_negative: bool = False,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> float:
        from .data_integrity_helpers import NumericValidator

        return NumericValidator.validate_numeric_value(value, variable_name, allow_zero, allow_negative, min_value, max_value)

    @staticmethod
    def validate_expiry_value(expiry: Any, variable_name: str = "expiry") -> float:
        from .data_integrity_helpers import FinancialValidator

        return FinancialValidator.validate_expiry_value(expiry, variable_name)

    @staticmethod
    def validate_strike_price(strike: Any, variable_name: str = "strike_price") -> float:
        from .data_integrity_helpers import FinancialValidator

        return FinancialValidator.validate_strike_price(strike, variable_name)

    @staticmethod
    def validate_option_price(price: Any, variable_name: str = "option_price") -> float:
        from .data_integrity_helpers import FinancialValidator

        return FinancialValidator.validate_option_price(price, variable_name)

    @staticmethod
    def validate_numpy_array(
        array: Any,
        variable_name: str,
        expected_shape: Optional[Tuple[int, ...]] = None,
        min_length: Optional[int] = None,
        allow_empty: bool = False,
    ) -> np.ndarray:
        from .data_integrity_helpers import ArrayValidator

        return ArrayValidator.validate_numpy_array(array, variable_name, expected_shape, min_length, allow_empty)

    @staticmethod
    def validate_json_data(json_data: Any, variable_name: str = "json_data") -> Union[Dict, List]:
        from .data_integrity_helpers import JsonValidator

        return JsonValidator.validate_json_data(json_data, variable_name)

    @staticmethod
    def validate_surface_prediction_result(
        prediction_result: Any, variable_name: str = "surface_prediction"
    ) -> Tuple[float, float, float, float, float, float]:
        from .data_integrity_helpers import SurfaceValidator

        return SurfaceValidator.validate_surface_prediction_result(prediction_result, variable_name)

    @staticmethod
    def validate_bid_ask_prices(bid_price: Any, ask_price: Any, variable_prefix: str = "price") -> Tuple[float, float]:
        from .data_integrity_helpers import FinancialValidator

        return FinancialValidator.validate_bid_ask_prices(bid_price, ask_price, variable_prefix)

    @staticmethod
    def validate_gp_surface_object(surface: Any, variable_name: str = "gp_surface") -> Any:
        from .data_integrity_helpers import SurfaceValidator

        return SurfaceValidator.validate_gp_surface_object(surface, variable_name)

    @staticmethod
    def log_validation_success(variable_name: str, value: Any) -> None:
        logger.debug(f"[DATA_VALIDATION] ✓ {variable_name} validated successfully: {type(value)} = {value}")

    @staticmethod
    def create_validation_summary(validations: List[Tuple[str, Any]]) -> str:
        summary_lines = ["=== DATA VALIDATION SUMMARY ==="]
        from ..time_utils import get_current_utc

        summary_lines.append(f"Timestamp: {get_current_utc().isoformat()}")
        summary_lines.append(f"Validated {len(validations)} variables:")

        for variable_name, value in validations:
            value_str = str(value)
            if len(value_str) > _CONST_50:
                value_str = value_str[:47] + "..."
            summary_lines.append(f"  ✓ {variable_name}: {type(value).__name__} = {value_str}")

        summary_lines.append("=== END VALIDATION SUMMARY ===")
        return "\n".join(summary_lines)
