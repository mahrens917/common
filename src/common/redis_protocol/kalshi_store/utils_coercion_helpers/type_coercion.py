"""Type coercion utilities for Redis data conversion."""

from typing import Any, Dict, List


def coerce_mapping(candidate: Any) -> Dict[str, Any]:
    """
    Convert candidate to dict, returning empty dict if conversion fails.

    Accepts mapping-like objects that expose ``items``.
    """
    if isinstance(candidate, dict):
        return candidate
    if hasattr(candidate, "items"):
        try:
            return dict(candidate.items())
        except (TypeError, ValueError, AttributeError):
            return {}
    return {}


def coerce_sequence(candidate: Any) -> List[Any]:
    """Convert candidate to a list, falling back to empty list on failure."""
    if candidate is None:
        return []
    if isinstance(candidate, (list, tuple, set)):
        return list(candidate)
    if hasattr(candidate, "__iter__"):
        try:
            return list(candidate)
        except (TypeError, ValueError, AttributeError):
            return []
    return []


def string_or_default(value: Any, fallback_value: str = "", *, trim: bool = False) -> str:
    """Coerce value to string with optional whitespace trimming and byte decoding."""
    if isinstance(value, str):
        return value.strip() if trim else value
    if isinstance(value, (bytes, bytearray)):
        decoded = value.decode("utf-8", "ignore")
        return decoded.strip() if trim else decoded
    if value is None:
        return fallback_value
    coerced = str(value)
    return coerced.strip() if trim else coerced


def int_or_default(value: Any, fallback_value: int = 0) -> int:
    """Public wrapper for int coercion helper."""
    if value is None:
        return fallback_value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (str, bytes, bytearray)):
        try:
            text = value.decode("utf-8", "ignore") if isinstance(value, (bytes, bytearray)) else value
            return int(float(text))
        except (
            TypeError,
            ValueError,
        ):
            return fallback_value
    return fallback_value


def float_or_default(
    value: Any,
    fallback_value: float = 0.0,
    *,
    raise_on_error: bool = False,
    error_message: str | None = None,
) -> float:
    """
    Coerce value to float with optional error raising.

    Delegates to canonical implementation in common.utils.numeric.

    When ``raise_on_error`` is False (default), this mirrors ``_float_or_default`` and
    returns the provided ``fallback_value`` for invalid inputs. When True, a ``ValueError`` is
    raised using ``error_message`` if provided.
    """
    from common.utils.numeric import coerce_float_default, coerce_float_strict

    if not raise_on_error:
        return coerce_float_default(value, fallback_value)

    if value is None:
        message = error_message.format(value=value) if error_message else "Expected numeric value"
        raise ValueError(message)

    try:
        return coerce_float_strict(value)
    except ValueError as exc:
        message = error_message.format(value=value) if error_message else f"Expected numeric value, got {value!r}"
        raise ValueError(message) from exc


def bool_or_default(
    value: Any,
    fallback_value: bool,
    *,
    parse_strings: bool = False,
) -> bool:
    """
    Coerce common boolean representations or return fallback_value.

    When ``parse_strings`` is True, accepts typical truthy/falsey strings.
    """
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    if parse_strings and isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "on", "1"}:
            return True
        if lowered in {"false", "no", "off", "0"}:
            return False
    return fallback_value


__all__ = [
    "bool_or_default",
    "coerce_mapping",
    "coerce_sequence",
    "float_or_default",
    "int_or_default",
    "string_or_default",
]
