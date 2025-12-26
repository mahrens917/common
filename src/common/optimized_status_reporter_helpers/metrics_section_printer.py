"""
Message and weather metrics printer.

Formats and prints message metrics and weather data metrics sections.
"""

from typing import Any, Dict

from common.config.weather import get_weather_settings

from .base_printer import StatusLinePrinterBase


class MetricsSectionPrinter(StatusLinePrinterBase):
    """Prints message and weather metrics sections."""

    def print_message_metrics_section(self, status_data: Dict[str, Any]) -> None:
        """Print message metrics section."""
        self._emit_status_line()
        self._emit_status_line("📈 Message Metrics (Past 60 Seconds):")
        deribit_messages = self.data_coercion.int_or_default(status_data.get("deribit_messages_60s"), 0)
        self._emit_status_line(f"  🟢 Deribit Messages - {deribit_messages:,}")

        kalshi_status = self.data_coercion.coerce_mapping(status_data.get("kalshi_market_status"))
        kalshi_trading_active = kalshi_status.get("trading_active")
        if kalshi_trading_active is False:
            self._emit_status_line("  ⚪ Kalshi Messages - N/A (exchange inactive)")
        else:
            kalshi_messages = self.data_coercion.int_or_default(status_data.get("kalshi_messages_60s"), 0)
            self._emit_status_line(f"  🟢 Kalshi Messages - {kalshi_messages:,}")

        cfb_msgs = self.data_coercion.int_or_default(status_data.get("cfb_messages_60s"), None)
        self._emit_status_line(f"  🟢 CFB Messages - {cfb_msgs:,}")

    def print_weather_metrics_section(self, status_data: Dict[str, Any]) -> None:
        """Print weather data metrics section."""
        self._emit_status_line()
        self._emit_status_line("📈 Temperature Change Metrics (Past 65 Minutes):")

        weather_settings = get_weather_settings()
        raw_asos_source = weather_settings.sources.asos_source
        if raw_asos_source:
            asos_source = raw_asos_source.lower()
        else:
            asos_source = ""
        if asos_source == "off":
            self._emit_status_line("  ⚪ ASOS Temperature Changes - DISABLED")
        else:
            asos_changes = self.data_coercion.int_or_default(status_data.get("asos_messages_65m"), 0)
            self._emit_status_line(f"  🟢 ASOS Temperature Changes - {asos_changes:,}")

        metar_changes = self.data_coercion.int_or_default(status_data.get("metar_messages_65m"), None)
        self._emit_status_line(f"  🟢 METAR Temperature Changes - {metar_changes:,}")

    def print_all_health_sections(self, status_data: Dict[str, Any]) -> None:
        """Print all health sections (message and weather metrics)."""
        self.print_message_metrics_section(status_data)
        self.print_weather_metrics_section(status_data)

    def print_tracker_status_section(self, tracker_status: Dict[str, Any]) -> None:
        """Print tracker status section."""
        self._emit_status_line()
        self._emit_status_line("🎯 Tracker Status:")
        if tracker_status:
            status_summary = self.data_coercion.string_or_default(
                tracker_status.get("status_summary"),
                "Unknown",
            )
            running = self.data_coercion.bool_or_default(tracker_status.get("running"), None)
            enabled = self.data_coercion.bool_or_default(tracker_status.get("enabled"), None)
            if not enabled and not running:
                status_summary = "🔴 Stopped | Disabled"
            self._emit_status_line(f"  {status_summary}")
        else:
            self._emit_status_line("  🔴 Tracker status unavailable")
        self._emit_status_line("=" * 60)
