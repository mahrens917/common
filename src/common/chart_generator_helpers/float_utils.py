"""Shared float parsing helpers for chart generator components."""

import logging
from typing import Optional

from common.parsing_utils import safe_float_parse

logger = logging.getLogger(__name__)


def safe_float(value: Optional[str]) -> Optional[float]:
    """Parse a float value while rejecting NaN/inf and treating empties as None."""
    if value in (None, ""):
        return None
    try:
        return safe_float_parse(value, allow_nan_inf=False)
    except ValueError as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to parse float: value=%r, error=%s", value, exc)
        return None
