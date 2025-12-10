"""
Report printing coordinator for OptimizedStatusReporter.

Extracted from OptimizedStatusReporter to reduce class size.
"""

from typing import Any, Dict


class ReportPrinterCoordinator:
    """Coordinates printing of status report sections."""

    def __init__(
        self,
        emit_func,
        data_coercion,
        section_printer,
        service_printer,
        metrics_printer,
        weather_generator,
        process_manager,
    ):
        """Initialize printer coordinator."""
        self._emit = emit_func
        self._data_coercion = data_coercion
        self._section_printer = section_printer
        self._service_printer = service_printer
        self._metrics_printer = metrics_printer
        self._weather_generator = weather_generator
        self._process_manager = process_manager

    async def print_status_report(self, status_data: Dict[str, Any]):
        """Print comprehensive status report using printers."""
        from common.time_utils import get_current_utc

        current_time = get_current_utc().strftime("%Y-%m-%d %H:%M:%S")
        self._emit("=" * 60)

        kalshi_status = self._data_coercion.coerce_mapping(status_data.get("kalshi_market_status"))
        self._section_printer.print_exchange_info(current_time, kalshi_status)
        self._emit()
        self._section_printer.print_price_info(status_data)
        self._section_printer.print_weather_info(status_data, self._weather_generator)

        self._emit()
        self._emit("📝 System Update:")

        tracker_status = self._data_coercion.coerce_mapping(status_data.get("tracker_status"))
        log_activity_map = status_data.get("log_activity") or {}
        healthy, total = self._service_printer.print_managed_services(
            self._process_manager, tracker_status, log_activity_map
        )
        self._service_printer.print_monitor_service(self._process_manager, log_activity_map)

        self._emit(f"📊 Process Summary: {healthy}/{total} running")
        self._metrics_printer.print_all_health_sections(status_data)
        self._section_printer.print_tracker_status_section(
            status_data,
            self._data_coercion.string_or_default,
            self._data_coercion.bool_or_default,
        )

    def generate_weather_section(self, weather_temperatures: Dict[str, Any]) -> list[str]:
        """Delegate to the weather generator when available."""
        if self._weather_generator is None:
            return []
        return self._weather_generator.generate_weather_section(weather_temperatures)
