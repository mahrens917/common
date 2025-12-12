"""JSON data validation for data integrity checks."""

import json
import logging
from typing import Dict, List, Union

from ..data_integrity_validator import DataIntegrityError

logger = logging.getLogger(__name__)


class JsonValidator:
    """Validator for JSON data to prevent decode errors."""

    @staticmethod
    def validate_json_data(json_data: object, variable_name: str = "json_data") -> Union[Dict, List]:
        """
        Validate JSON data to prevent decode errors.

        Args:
            json_data: The JSON data to validate
            variable_name: Name of the variable for error messages

        Returns:
            The validated JSON data

        Raises:
            DataIntegrityError: If validation fails
        """
        # Check for None
        if json_data is None:
            raise DataIntegrityError(f"None JSON data not allowed for {variable_name}")

        # If it's a string, try to parse it
        if isinstance(json_data, str):
            if len(json_data) == 0:
                raise DataIntegrityError(f"Empty JSON string not allowed for {variable_name}")

            try:
                parsed_data = json.loads(json_data)
            except json.JSONDecodeError as e:  # policy_guard: allow-silent-handler
                raise DataIntegrityError(f"Invalid JSON string for {variable_name}") from e
            else:
                return parsed_data

        # If it's already a dict or list, validate structure
        elif isinstance(json_data, (dict, list)):
            return json_data

        else:
            raise DataIntegrityError(f"Invalid JSON data type for {variable_name}: {type(json_data)}")
