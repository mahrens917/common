"""Shared helpers for validating required dictionary fields."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Callable, Type, TypeVar

ExcT = TypeVar("ExcT", bound=Exception)


def validate_required_fields(
    payload: Mapping[str, Any],
    required_fields: Iterable[str],
    *,
    error_cls: Type[ExcT] = ValueError,
    on_missing: Callable[[list[str], Mapping[str, Any]], ExcT] | None = None,
) -> None:
    """
    Ensure all required fields are present in *payload*.

    Args:
        payload: Mapping to inspect.
        required_fields: Field names that must be present.
        error_cls: Exception type to raise when fields are missing.
        on_missing: Optional factory returning a custom exception instance.

    Raises:
        TypeError: If payload is not a mapping.
        error_cls: When any required field is absent.
    """
    try:
        missing_fields = sorted(set(required_fields) - set(payload))
    except TypeError:
        raise TypeError(f"payload must be a Mapping, got {type(payload).__name__}")
    if not missing_fields:
        return

    if on_missing:
        raise on_missing(missing_fields, payload)

    fields_display = ", ".join(missing_fields)
    raise error_cls(f"Payload missing required field(s): {fields_display}")


__all__ = [
    "validate_required_fields",
]
"""Shared probability normalization helpers."""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


def clamp_probability(value: Optional[float]) -> Optional[float]:
    """
    Clamp a probability-like value into [0, 1].

    Returns None for non-numeric or non-finite inputs.
    """
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to convert probability value to float: value=%r, error=%s", value, exc)
        return None
    if not math.isfinite(numeric):
        return None
    return max(0.0, min(1.0, numeric))


def first_valid_probability(*candidates: Optional[float]) -> Optional[float]:
    """
    Return the first candidate that can be clamped to [0, 1].

    Useful when multiple fields may carry the same signal.
    """
    for candidate in candidates:
        clamped = clamp_probability(candidate)
        if clamped is not None:
            return clamped
    return None
