"""Mixin classes for OptimizedStatusReporter functionality."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional
from unittest.mock import Mock

from common.truthy import pick_if

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from common.optimized_status_reporter_helpers.log_activity_formatter import (
        LogActivityFormatter,
    )


def _ensure_str_list(lines: Any) -> list[str]:
    if lines is None:
        _none_guard_value = []
        return _none_guard_value
    if isinstance(lines, list):
        return [str(item) for item in lines]
    try:
        return [str(item) for item in list(lines)]
    except TypeError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Expected data validation or parsing failure")
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
        weather_temperatures_raw = status_data.get("weather_temperatures")
        if isinstance(weather_temperatures_raw, dict):
            weather_temperatures = weather_temperatures_raw
        else:
            weather_temperatures = dict()
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
