"""GP surface and prediction result validation for data integrity checks."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, Tuple

from ..data_integrity_validator import DataIntegrityError
from .numeric_validator import NumericValidator

logger = logging.getLogger(__name__)


# Constants
_CONST_6 = 6


class SurfaceValidator:
    """Validator for GP surface objects and prediction results."""

    @staticmethod
    def validate_surface_prediction_result(
        prediction_result: object, variable_name: str = "surface_prediction"
    ) -> Tuple[float, float, float, float, float, float]:
        """
        Validate surface prediction results from GP models.

        Args:
            prediction_result: The prediction result to validate
            variable_name: Name of the variable for error messages

        Returns:
            Validated tuple of (g_fit, h_fit, p_fit, S_fit, I_fit, p_micro_fit)

        Raises:
            DataIntegrityError: If validation fails
        """
        # Check for None
        if prediction_result is None:
            raise DataIntegrityError(f"None prediction result not allowed for {variable_name}")

        if not isinstance(prediction_result, Iterable):
            raise DataIntegrityError(f"Cannot iterate {variable_name} for tuple conversion: {type(prediction_result)}")

        result_tuple = tuple(prediction_result)

        if len(result_tuple) != _CONST_6:
            raise DataIntegrityError(f"{variable_name} must have 6 elements, got {len(result_tuple)}")

        # Validate each element
        # g_fit is a log spread value, so negative values are allowed (log of values < 1)
        g_fit = NumericValidator.validate_numeric_value(result_tuple[0], f"{variable_name}[0] (g_fit)", allow_negative=True)
        # h_fit is a logit intensity value, so negative values are allowed (logit can be negative)
        h_fit = NumericValidator.validate_numeric_value(result_tuple[1], f"{variable_name}[1] (h_fit)", allow_negative=True)
        # p_fit can be negative if it's a log micro price
        p_fit = NumericValidator.validate_numeric_value(result_tuple[2], f"{variable_name}[2] (p_fit)", allow_negative=True)
        S_fit = NumericValidator.validate_numeric_value(result_tuple[3], f"{variable_name}[3] (S_fit)", allow_zero=False)
        I_fit = NumericValidator.validate_numeric_value(result_tuple[4], f"{variable_name}[4] (I_fit)", min_value=0.0, max_value=1.0)
        p_micro_fit = NumericValidator.validate_numeric_value(result_tuple[5], f"{variable_name}[5] (p_micro_fit)", allow_zero=False)

        return g_fit, h_fit, p_fit, S_fit, I_fit, p_micro_fit

    @staticmethod
    def validate_gp_surface_object(surface: object, variable_name: str = "gp_surface") -> Any:
        """
        Validate GP surface objects have required methods.

        Args:
            surface: The GP surface object to validate
            variable_name: Name of the variable for error messages

        Returns:
            The validated surface object

        Raises:
            DataIntegrityError: If validation fails
        """
        # Check for None
        if surface is None:
            raise DataIntegrityError(f"None surface object not allowed for {variable_name}")

        # Check for required methods
        required_methods = ["predict_three_surfaces"]
        missing_methods = []

        for method_name in required_methods:
            if not hasattr(surface, method_name):
                missing_methods.append(method_name)

        if missing_methods:
            available_methods = [method for method in dir(surface) if not method.startswith("_")]
            raise DataIntegrityError(
                f"{variable_name} missing required methods: {missing_methods}. " f"Available methods: {available_methods}"
            )

        return surface
