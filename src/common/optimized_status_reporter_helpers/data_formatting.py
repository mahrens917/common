"""
Data formatting utilities for status display.

Provides consistent formatting for percentages and other display values.
"""

from typing import Any


class DataFormatting:
    """Utilities for formatting data values for display."""

    @staticmethod
    def format_percentage(value: Any) -> str:
        """Format value as percentage with one decimal place."""
        if value is None:
            return "N/A"
        if isinstance(value, bool):
            return f"{float(value):.1f}%"
        if isinstance(value, (int, float)):
            return f"{float(value):.1f}%"
        if isinstance(value, (str, bytes, bytearray)):
            try:
                text = value.decode("utf-8", "ignore") if isinstance(value, (bytes, bytearray)) else value
                return f"{float(text):.1f}%"
            except (
                TypeError,
                ValueError,
            ):
                return "N/A"
        return "N/A"
