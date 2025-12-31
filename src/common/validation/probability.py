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
