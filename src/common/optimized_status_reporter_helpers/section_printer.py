"""
Section printing helpers for OptimizedStatusReporter.

Extracted from OptimizedStatusReporter to reduce class size.
"""

from typing import Any, Dict, Optional


class SectionPrinter:
    """Handles printing of individual status report sections."""

    def __init__(self, emit_func):
        """
        Initialize section printer.

        Args:
            emit_func: Function to emit status lines (signature: (str, *, log: bool) -> None)
        """
        self._emit = emit_func

    def print_exchange_info(self, current_time: str, kalshi_status: Dict[str, Any]) -> None:
        """Print exchange status section."""
        self._emit("📊 Exchange Info:")
        self._emit(f"  🕐 Time: {current_time}")

        if "error" in kalshi_status:
            self._emit("  ⚪ Kalshi: UNAVAILABLE")
            return

        exchange_active = kalshi_status.get("exchange_active")
        trading_active = kalshi_status.get("trading_active")

        self._emit(self._format_exchange_status_line("Kalshi Exchange", exchange_active))
        self._emit(self._format_exchange_status_line("Kalshi Trading", trading_active))

    def _format_exchange_status_line(self, label: str, flag: Optional[bool]) -> str:
        """Format exchange status line with emoji."""
        if flag is None:
            return f"  ⚪ {label}: UNKNOWN"
        if flag:
            emoji = "🟢"
            state = "ACTIVE"
        else:
            emoji = "🔴"
            state = "INACTIVE"
        return f"  {emoji} {label}: {state}"

    def print_price_info(self, status_data: Dict[str, Any]) -> None:
        """Print price information section."""
        self._emit("💰 Price Info:")
        btc_price = status_data.get("btc_price")
        eth_price = status_data.get("eth_price")
        if btc_price:
            self._emit(f"  ₿ BTC: ${btc_price:,.2f}")
        else:
            self._emit("  ₿ BTC: N/A")
        if eth_price:
            self._emit(f"  Ξ ETH: ${eth_price:,.2f}")
        else:
            self._emit("  Ξ ETH: N/A")

    def print_weather_info(self, status_data: Dict[str, Any], weather_generator) -> None:
        """Print weather section using weather generator."""
        weather_lines = weather_generator.generate_weather_section(status_data)
        if not weather_lines:
            return

        self._emit()
        for line in weather_lines:
            self._emit(line)

    def print_tracker_status_section(
        self, status_data: Dict[str, Any], string_or_default_func, bool_or_default_func
    ) -> None:
        """Print tracker status section."""
        self._emit()
        self._emit("🎯 Tracker Status:")
        tracker_status = status_data.get("tracker_status")
        if not isinstance(tracker_status, dict):
            tracker_status = None

        if tracker_status:
            status_summary = string_or_default_func(tracker_status.get("status_summary"), "Unknown")
            running = bool_or_default_func(tracker_status.get("running"), None)
            enabled_raw = tracker_status.get("enabled")
            enabled = bool_or_default_func(
                enabled_raw, enabled_raw if enabled_raw is not None else True
            )
            if not enabled and not running:
                status_summary = "🔴 Stopped | Disabled"
            self._emit(f"  {status_summary}")
        else:
            self._emit("  🔴 Tracker status unavailable")
        self._emit("=" * 60)
