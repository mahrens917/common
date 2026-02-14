from __future__ import annotations

"""Shared logging and exception helpers for time_utils package."""

import logging

logger = logging.getLogger(__name__)


class AstronomicalComputationError(RuntimeError):
    """Raised when astronomical calculations cannot produce a valid result."""


EARTH_AXIAL_TILT_DEG = 23.4393

__all__ = ["AstronomicalComputationError", "EARTH_AXIAL_TILT_DEG", "logger"]
