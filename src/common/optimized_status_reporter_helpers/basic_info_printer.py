"""
Basic information printer - exchange, price, weather, services.

Prints simple sections without complex sub-components.
"""

from typing import Any, Dict, Optional, Tuple

from src.common.health.log_activity_monitor import LogActivity
from src.common.monitoring import ProcessStatus
from src.common.optimized_status_reporter_helpers.status_line import emit_status_line

from .monitor_service_printer import MonitorServicePrinter


class BasicInfoPrinter:
    """Prints basic information sections."""

    def __init__(self, process_manager, service_status_formatter):
        self.process_manager = process_manager
        self.service_status_formatter = service_status_formatter
        self.monitor_printer = MonitorServicePrinter(process_manager, service_status_formatter)
        self._emit_status_line = emit_status_line

    def print_exchange_info(self, current_time: str, kalshi_status: Dict[str, Any]) -> None:
        """Print exchange information section."""
        self._emit_status_line("📊 Exchange Info:")
        self._emit_status_line(f"  🕐 Time: {current_time}")

        if "error" in kalshi_status:
            self._emit_status_line("  ⚪ Kalshi: UNAVAILABLE")
            return

        exchange_active = kalshi_status.get("exchange_active")
        trading_active = kalshi_status.get("trading_active")

        self._emit_status_line(
            self._format_exchange_status_line("Kalshi Exchange", exchange_active)
        )
        self._emit_status_line(self._format_exchange_status_line("Kalshi Trading", trading_active))

    @staticmethod
    def _format_exchange_status_line(label: str, flag: Optional[bool]) -> str:
        """Format exchange status line with emoji and state."""
        if flag is None:
            return f"  ⚪ {label}: UNKNOWN"
        if flag:
            emoji = "🟢"
            state = "ACTIVE"
        else:
            emoji = "🔴"
            state = "INACTIVE"
        return f"  {emoji} {label}: {state}"

    def print_price_info(self, btc_price: Optional[float], eth_price: Optional[float]) -> None:
        """Print price information section."""
        self._emit_status_line("💰 Price Info:")
        if btc_price:
            self._emit_status_line(f"  ₿ BTC: ${btc_price:,.2f}")
        else:
            self._emit_status_line("  ₿ BTC: N/A")
        if eth_price:
            self._emit_status_line(f"  Ξ ETH: ${eth_price:,.2f}")
        else:
            self._emit_status_line("  Ξ ETH: N/A")

    def print_weather_section(self, weather_lines: list) -> None:
        """Print weather section if data available."""
        if not weather_lines:
            return

        self._emit_status_line()
        for line in weather_lines:
            self._emit_status_line(line)

    def print_managed_services(
        self, tracker_status: Dict[str, Any], log_activity_map: Dict[str, LogActivity]
    ) -> Tuple[int, int]:
        """Print all managed services and return healthy/total counts."""
        healthy_count = 0
        total_count = 0

        for service_name in sorted(self.process_manager.services):
            info = self.process_manager.process_info.get(service_name)
            running = bool(info and info.status == ProcessStatus.RUNNING)
            activity = log_activity_map.get(service_name)

            service_line = self.service_status_formatter.build_service_status_line(
                service_name=service_name,
                info=info,
                running=running,
                tracker_status=tracker_status,
                activity=activity,
            )
            self._emit_status_line(service_line)

            total_count += 1
            if running:
                healthy_count += 1

        return healthy_count, total_count

    def print_monitor_service(self, log_activity_map: Dict[str, LogActivity]) -> None:
        """Print monitor service status line."""
        line = self.monitor_printer.build_monitor_status_line(log_activity_map)
        if line:
            self._emit_status_line(line)
