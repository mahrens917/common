"""
Formatting utilities for status display: time durations and data values.
"""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Any

_CONST_24 = 24
_CONST_60 = 60
_CONST_7 = 7


class TimeFormatter:
    """Formats time durations for human readability."""

    @staticmethod
    def _format_time_unit(value: int, remainder: int, unit: str, remainder_unit: str) -> str:
        """Format time with optional remainder component."""
        if remainder:
            return f"{value}{unit} {remainder}{remainder_unit}"
        return f"{value}{unit}"

    @staticmethod
    def _normalize_seconds(seconds: float) -> int | None:
        """Normalize input to integer seconds, return None if invalid."""
        if isinstance(seconds, timedelta):
            total_seconds = seconds.total_seconds()
        else:
            try:
                total_seconds = float(seconds)
            except (  # policy_guard: allow-silent-handler
                TypeError,
                ValueError,
            ):
                return None

        if not math.isfinite(total_seconds):
            return None

        return max(int(total_seconds), 0)

    @classmethod
    def humanize_duration(cls, seconds: float) -> str:
        """Convert seconds into a compact human-friendly duration."""
        normalized_seconds = cls._normalize_seconds(seconds)
        if normalized_seconds is None:
            _none_guard_value = "unknown"
            return _none_guard_value

        if normalized_seconds < _CONST_60:
            return f"{normalized_seconds}s"

        minutes, sec = divmod(normalized_seconds, _CONST_60)
        if minutes < _CONST_60:
            return cls._format_time_unit(minutes, sec, "m", "s")

        hours, minutes = divmod(minutes, _CONST_60)
        if hours < _CONST_24:
            return cls._format_time_unit(hours, minutes, "h", "m")

        days, hours = divmod(hours, _CONST_24)
        if days < _CONST_7:
            return cls._format_time_unit(days, hours, "d", "h")

        weeks, days = divmod(days, _CONST_7)
        return cls._format_time_unit(weeks, days, "w", "d")


class DataFormatting:
    """Utilities for formatting data values for display."""

    @staticmethod
    def format_percentage(value: Any) -> str:
        """Format value as percentage with one decimal place."""
        if value is None:
            _none_guard_value = "N/A"
            return _none_guard_value
        if isinstance(value, bool):
            return f"{float(value):.1f}%"
        if isinstance(value, (int, float)):
            return f"{float(value):.1f}%"
        if isinstance(value, (str, bytes, bytearray)):
            try:
                text = value.decode("utf-8", "ignore") if isinstance(value, (bytes, bytearray)) else value
                return f"{float(text):.1f}%"
            except (  # policy_guard: allow-silent-handler
                TypeError,
                ValueError,
            ):
                return "N/A"
        return "N/A"
