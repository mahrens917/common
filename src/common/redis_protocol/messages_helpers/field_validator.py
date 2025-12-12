"""Field validation helpers for Redis hash data"""

from typing import Any, Dict


def validate_required_field(hash_data: Dict[str, Any], field_name: str, context: str = "") -> Any:
    """
    Validate that a required field exists in hash data.

    Args:
        hash_data: Dictionary of hash data
        field_name: Name of required field
        context: Additional context for error message

    Returns:
        Field value

    Raises:
        RuntimeError: If field is missing
    """
    value = hash_data.get(field_name)
    if value is None:
        context_suffix = f" in {context}" if context else ""
        raise RuntimeError(f"FAIL-FAST: Missing required {field_name} field{context_suffix}. " f"Cannot proceed with empty {field_name}.")
    return value


def validate_float_field(hash_data: Dict[str, Any], field_name: str, context: str = "") -> float:
    """
    Validate and convert a field to float.

    Args:
        hash_data: Dictionary of hash data
        field_name: Name of field to convert
        context: Additional context for error message

    Returns:
        Float value

    Raises:
        RuntimeError: If field is missing or cannot be converted
    """
    value_str = validate_required_field(hash_data, field_name, context)
    try:
        return float(value_str)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError(f"Invalid {field_name} value '{value_str}' - cannot convert to float") from exc
