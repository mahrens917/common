import logging
import math
import re
from typing import Any, Optional, Set

from common.redis_protocol.converters import FloatCoercionError, coerce_float

from .errors import PricingValidationError

logger = logging.getLogger(__name__)

_NUMERIC_PRICE_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_NON_NUMERIC_SENTINELS = {"none", "null", "nan"}
_SANITIZED_PRICE_VALUES_LOGGED: Set[str] = set()


def _normalize_numeric_string(value: str) -> Optional[str]:
    """
    Normalize numeric strings used in market data.

    Returns the cleaned representation or ``None`` when the value should be
    treated as missing.
    """
    stripped = value.strip()
    if not stripped:
        return None

    lowered = stripped.lower()
    if lowered in _NON_NUMERIC_SENTINELS:
        return None

    if stripped.endswith("%"):
        stripped = stripped[:-1].strip()
        if not stripped:
            return None

    if stripped.startswith("+"):
        stripped = stripped[1:]

    if not _NUMERIC_PRICE_PATTERN.match(stripped):
        if (
            stripped not in _SANITIZED_PRICE_VALUES_LOGGED
            and value not in _SANITIZED_PRICE_VALUES_LOGGED
        ):
            _SANITIZED_PRICE_VALUES_LOGGED.add(stripped)
            _SANITIZED_PRICE_VALUES_LOGGED.add(value)
            logger.debug("Skipping non-numeric market price value: %r", value)
        return None

    return stripped


def _coerce_price(value: Any, *, default: float = 0.0) -> float:
    """Convert *value* to float, raising on invalid numeric data.

    Delegates to canonical implementation in common.redis_protocol.converters.
    Preserves tracker-specific behavior: percentage handling, custom error types.
    """

    # Handle None with default
    if value is None:
        return default

    # Apply tracker-specific string normalization (handles percentages)
    if isinstance(value, str):
        normalized = _normalize_numeric_string(value)
        if normalized is None:
            raise PricingValidationError(value)
        value = normalized

    # Delegate to canonical coercion with NaN rejection
    def _raise_pricing_error(exc):
        raise PricingValidationError(str(value)) from exc

    try:
        result = coerce_float(value, allow_none=False, finite_only=True)
        if result is None:
            # Should not happen with allow_none=False, but defensive check
            _raise_pricing_error(None)
            raise RuntimeError("Unreachable")
    except (FloatCoercionError, ValueError, TypeError) as exc:
        _raise_pricing_error(exc)
        raise RuntimeError("Unreachable")
    return result


def _coerce_optional_price(value: Any) -> Optional[float]:
    """Convert *value* to float, returning None when it is blank or missing.

    Delegates to canonical implementation in common.redis_protocol.converters.
    Preserves tracker-specific behavior: percentage handling, custom error types.
    """

    # Handle None
    if value is None:
        return None

    # Check for NaN on numeric inputs (raise error before canonical delegation)
    if isinstance(value, float) and math.isnan(value):
        raise PricingValidationError(str(value), reason="Numeric value is NaN")

    # Apply tracker-specific string normalization (handles percentages)
    if isinstance(value, str):
        normalized = _normalize_numeric_string(value)
        if normalized is None:
            return None
        value = normalized

    # Delegate to canonical coercion
    def _raise_pricing_error(exc):
        raise PricingValidationError(str(value)) from exc

    try:
        result = coerce_float(value, allow_none=True, finite_only=False)
        # Check result for NaN/Inf after coercion
        if result is not None and not math.isfinite(result):
            _raise_pricing_error(None)
    except (FloatCoercionError, ValueError, TypeError) as exc:
        _raise_pricing_error(exc)
    else:
        return result


__all__ = [
    "_coerce_optional_price",
    "_coerce_price",
    "_normalize_numeric_string",
    "_SANITIZED_PRICE_VALUES_LOGGED",
]
