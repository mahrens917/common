"""Array validation for data integrity checks."""

import logging
from typing import Optional, Tuple

import numpy as np

from ..data_integrity_validator import DataIntegrityError

logger = logging.getLogger(__name__)


class ArrayValidator:
    """Validator for numpy arrays with comprehensive checks."""

    @staticmethod
    def _convert_to_array(array: object, variable_name: str) -> np.ndarray:
        """Convert input to numpy array."""
        if array is None:
            raise DataIntegrityError(f"None array not allowed for {variable_name}")
        try:
            return np.asarray(array)
        except (TypeError, ValueError) as exc:
            raise DataIntegrityError(f"Cannot convert {variable_name} to numpy array") from exc

    @staticmethod
    def _validate_size_constraints(
        np_array: np.ndarray, variable_name: str, min_length: Optional[int], allow_empty: bool
    ) -> None:
        """Validate array size and length constraints."""
        if np_array.size == 0 and not allow_empty:
            raise DataIntegrityError(f"Empty array not allowed for {variable_name}")
        if min_length is not None and len(np_array) < min_length:
            raise DataIntegrityError(
                f"{variable_name} length {len(np_array)} below minimum {min_length}"
            )

    @staticmethod
    def _validate_shape(
        np_array: np.ndarray, variable_name: str, expected_shape: Optional[Tuple[int, ...]]
    ) -> None:
        """Validate array shape."""
        if expected_shape is not None and np_array.shape != expected_shape:
            raise DataIntegrityError(
                f"{variable_name} shape {np_array.shape} does not match expected {expected_shape}"
            )

    @staticmethod
    def _validate_finite_values(np_array: np.ndarray, variable_name: str) -> None:
        """Validate array contains only finite values (no NaN or infinity)."""
        if np.any(np.isnan(np_array)):
            nan_indices = np.where(np.isnan(np_array))
            raise DataIntegrityError(
                f"NaN values found in {variable_name} at indices: {nan_indices}"
            )
        if np.any(np.isinf(np_array)):
            inf_indices = np.where(np.isinf(np_array))
            raise DataIntegrityError(
                f"Infinite values found in {variable_name} at indices: {inf_indices}"
            )

    @classmethod
    def validate_numpy_array(
        cls,
        array: object,
        variable_name: str,
        expected_shape: Optional[Tuple[int, ...]] = None,
        min_length: Optional[int] = None,
        allow_empty: bool = False,
    ) -> np.ndarray:
        """
        Validate numpy arrays with comprehensive checks.

        Args:
            array: The array to validate
            variable_name: Name of the variable for error messages
            expected_shape: Expected shape (optional)
            min_length: Minimum required length (optional)
            allow_empty: Whether empty arrays are allowed

        Returns:
            The validated numpy array

        Raises:
            DataIntegrityError: If validation fails
        """
        np_array = cls._convert_to_array(array, variable_name)
        cls._validate_size_constraints(np_array, variable_name, min_length, allow_empty)
        cls._validate_shape(np_array, variable_name, expected_shape)
        cls._validate_finite_values(np_array, variable_name)
        return np_array
