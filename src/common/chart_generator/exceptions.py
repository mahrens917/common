from __future__ import annotations


class InsufficientDataError(Exception):
    """Raised when there is not enough data to render a chart."""


class ProgressNotificationError(RuntimeError):
    """Raised when the progress callback fails."""
