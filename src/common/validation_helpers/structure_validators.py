"""Data structure validation helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from .exceptions import ValidationError


class StructureValidators:
    """Validators for data structures (lists, dictionaries)."""

    @staticmethod
    def validate_list_not_empty(data_list: List[Any] | None, list_name: str = "list") -> bool:
        """Validate list is not None and not empty."""
        if data_list is None:
            raise ValidationError(f"{list_name} cannot be None")
        if len(data_list) == 0:
            raise ValidationError(f"{list_name} cannot be empty")
        return True

    @staticmethod
    def validate_dictionary_has_keys(
        data_dict: Dict[str, Any] | None, required_keys: List[str], dict_name: str = "dictionary"
    ) -> bool:
        """Validate dictionary contains all required keys."""
        if data_dict is None:
            raise ValidationError(f"{dict_name} cannot be None")
        missing_keys = []
        for key in required_keys:
            if key not in data_dict:
                missing_keys.append(key)
        if missing_keys:
            raise ValidationError(f"{dict_name} missing required keys: {missing_keys}")
        return True
