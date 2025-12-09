from __future__ import annotations

"""Shared logging and exception helpers for time_utils package."""

import logging

logger = logging.getLogger(__name__)


class AstronomicalComputationError(RuntimeError):
    """Raised when astronomical calculations cannot produce a valid result."""


__all__ = ["AstronomicalComputationError", "logger"]
