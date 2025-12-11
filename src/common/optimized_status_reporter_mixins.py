"""Mixin classes for OptimizedStatusReporter functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from unittest.mock import Mock

if TYPE_CHECKING:
    from common.optimized_status_reporter_helpers.log_activity_formatter import (
        LogActivityFormatter,
    )


def _ensure_str_list(lines: Any) -> list[str]:
    if lines is None:
        return []
    if isinstance(lines, list):
        return [str(item) for item in lines]
    try:
        return [str(item) for item in list(lines)]
    except TypeError:
        return [str(lines)]


def _generate_weather_lines(printer: Any, temperatures: Dict[str, Any]) -> list[str]:
    printer_generate = getattr(printer, "generate_weather_section", None)
    weather_generator = getattr(printer, "_weather_generator", None)

    if callable(printer_generate) and not isinstance(printer_generate, Mock):
        return _ensure_str_list(printer_generate(temperatures))

    if weather_generator:
        return _ensure_str_list(weather_generator.generate_weather_section(temperatures))

    if callable(printer_generate):
        return _ensure_str_list(printer_generate(temperatures))

    return []


class StatusReporterWeatherMixin:
    """Mixin for weather section generation."""

    _printer: Any

    def _generate_weather_section(self, status_data: Dict[str, Any]) -> list[str]:
        """Generate weather section lines via printer helpers."""
        weather_temperatures = status_data.get("weather_temperatures") or {}
        return _generate_weather_lines(self._printer, weather_temperatures)


class StatusReporterFormatterMixin:
    """Mixin for log activity formatting."""

    _log_activity_formatter: LogActivityFormatter

    def format_log_activity_short(self, service_name: str, activity: Optional[Any]) -> Optional[str]:
        """Expose log activity summaries for helpers."""
        return self._log_activity_formatter.format_log_activity_short(service_name, activity)

    def _format_log_activity_short(self, service_name: str, activity: Optional[Any]) -> Optional[str]:
        """Backward-compatible alias for log activity summarization."""
        return self.format_log_activity_short(service_name, activity)


__all__ = [
    "StatusReporterWeatherMixin",
    "StatusReporterFormatterMixin",
    "_ensure_str_list",
    "_generate_weather_lines",
]
