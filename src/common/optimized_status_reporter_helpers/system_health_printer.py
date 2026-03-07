"""
System resources health printer.

Formats and prints system resource usage information.
"""

from typing import Any

from common.redis_protocol.kalshi_store import utils_coercion


class SystemHealthPrinter:
    """Prints system resources health section."""

    def __init__(self, data_formatting):
        self.data_formatting = data_formatting
        self._emit_status_line = print

    def print_system_resources_section(self, system_resources_health: Any) -> None:
        """Print system resources health section."""
        self._emit_status_line()
        self._emit_status_line("💻 System Resources Health:")
        if system_resources_health:
            health_check = system_resources_health
            status_value = health_check.status.value
            if status_value == "healthy":
                status_icon = "✅"
            elif status_value == "degraded":
                status_icon = "⚠️"
            else:
                status_icon = "🔴"
            self._emit_status_line(f"  {status_icon} Overall Status - {health_check.status.value.title()}")
            if health_check.details:
                details = utils_coercion.coerce_mapping(health_check.details)
                cpu_usage = self.data_formatting.format_percentage(details.get("cpu_percent"))
                memory_usage = self.data_formatting.format_percentage(details.get("memory_percent"))
                disk_usage = self.data_formatting.format_percentage(details.get("disk_percent"))
                self._emit_status_line(f"  📊 CPU Usage: {cpu_usage}")
                self._emit_status_line(f"  🧠 Memory Usage: {memory_usage}")
                self._emit_status_line(f"  💾 Disk Usage: {disk_usage}")
            if health_check.message != "System resources normal":
                self._emit_status_line(f"  ⚠️ Issues: {health_check.message}")
        else:
            self._emit_status_line("  🔴 System Resources - Check Failed")
