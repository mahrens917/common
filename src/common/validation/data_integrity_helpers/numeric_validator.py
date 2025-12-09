"""Numeric value validation for data integrity checks."""

import logging
from typing import Optional

import numpy as np

from ..data_integrity_validator import DataIntegrityError

logger = logging.getLogger(__name__)


class NumericValidator:
    """Validator for numeric values with comprehensive constraint checking."""

    @staticmethod
    def _convert_to_float(value: object, variable_name: str) -> float:
        """Convert value to float and check for None."""
        if value is None:
            raise DataIntegrityError(f"None value not allowed for {variable_name}")
        if isinstance(value, (int, float, str, bytes)):
            try:
                return float(value)
            except (ValueError, TypeError):
                raise DataIntegrityError(
                    f"Cannot convert {variable_name} to numeric value: {value} (type: {type(value)}). Error"
                )

        raise DataIntegrityError(
            f"Cannot convert {variable_name} to numeric value: {value} (type: {type(value)})"
        )

    @staticmethod
    def _validate_finite(numeric_value: float, variable_name: str) -> None:
        """Validate value is finite (not NaN or infinity)."""
        if np.isnan(numeric_value):
            raise DataIntegrityError(f"NaN value not allowed for {variable_name}")
        if np.isinf(numeric_value):
            raise DataIntegrityError(
                f"Infinite value not allowed for {variable_name}: {numeric_value}"
            )

    @staticmethod
    def _validate_sign_constraints(
        numeric_value: float, variable_name: str, allow_zero: bool, allow_negative: bool
    ) -> None:
        """Validate zero and negative value constraints."""
        if not allow_zero and numeric_value == 0.0:
            raise DataIntegrityError(f"Zero value not allowed for {variable_name}")
        if not allow_negative and numeric_value < 0.0:
            raise DataIntegrityError(
                f"Negative value not allowed for {variable_name}: {numeric_value}"
            )

    @staticmethod
    def _validate_range(
        numeric_value: float,
        variable_name: str,
        min_value: Optional[float],
        max_value: Optional[float],
    ) -> None:
        """Validate value is within specified min/max range."""
        if min_value is not None and numeric_value < min_value:
            raise DataIntegrityError(
                f"{variable_name} below minimum: {numeric_value} < {min_value}"
            )
        if max_value is not None and numeric_value > max_value:
            raise DataIntegrityError(
                f"{variable_name} above maximum: {numeric_value} > {max_value}"
            )

    @classmethod
    def validate_numeric_value(
        cls,
        value: object,
        variable_name: str,
        allow_zero: bool = True,
        allow_negative: bool = False,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> float:
        """
        Validate that a value is a valid numeric value.

        Args:
            value: The value to validate
            variable_name: Name of the variable for error messages
            allow_zero: Whether zero values are allowed
            allow_negative: Whether negative values are allowed
            min_value: Minimum allowed value (optional)
            max_value: Maximum allowed value (optional)

        Returns:
            The validated numeric value as float

        Raises:
            DataIntegrityError: If validation fails
        """
        numeric_value = cls._convert_to_float(value, variable_name)
        cls._validate_finite(numeric_value, variable_name)
        cls._validate_sign_constraints(numeric_value, variable_name, allow_zero, allow_negative)
        cls._validate_range(numeric_value, variable_name, min_value, max_value)
        return numeric_value
