"""Tests for basic info printer module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from common.health.log_activity_monitor import LogActivity, LogActivityStatus
from common.monitoring import ProcessStatus
from common.optimized_status_reporter_helpers.basic_info_printer import BasicInfoPrinter


class TestBasicInfoPrinter:
    """Tests for BasicInfoPrinter class."""

    def test_init_creates_monitor_printer(self) -> None:
        """Initializes with monitor printer."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()

        printer = BasicInfoPrinter(process_manager, service_status_formatter)

        assert printer.process_manager == process_manager
        assert printer.service_status_formatter == service_status_formatter
        assert printer.monitor_printer is not None


class TestPrintExchangeInfo:
    """Tests for print_exchange_info method."""

    def test_prints_time(self) -> None:
        """Prints current time."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_exchange_info("2025-01-15 12:00:00", {})

        assert any("12:00:00" in str(line) for line in emitted)

    def test_prints_unavailable_on_error(self) -> None:
        """Prints unavailable when status has error."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_exchange_info("2025-01-15 12:00:00", {"error": "connection failed"})

        assert any("UNAVAILABLE" in str(line) for line in emitted)

    def test_prints_active_exchange_status(self) -> None:
        """Prints active status when exchange is active."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_exchange_info(
            "2025-01-15 12:00:00",
            {"exchange_active": True, "trading_active": True},
        )

        assert any("ACTIVE" in str(line) for line in emitted)

    def test_prints_inactive_exchange_status(self) -> None:
        """Prints inactive status when exchange is inactive."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_exchange_info(
            "2025-01-15 12:00:00",
            {"exchange_active": False, "trading_active": False},
        )

        assert any("INACTIVE" in str(line) for line in emitted)


class TestFormatExchangeStatusLine:
    """Tests for _format_exchange_status_line method."""

    def test_returns_unknown_when_flag_none(self) -> None:
        """Returns unknown status when flag is None."""
        result = BasicInfoPrinter._format_exchange_status_line("Test Label", None)

        assert "UNKNOWN" in result
        assert "⚪" in result

    def test_returns_active_when_flag_true(self) -> None:
        """Returns active status when flag is True."""
        result = BasicInfoPrinter._format_exchange_status_line("Test Label", True)

        assert "ACTIVE" in result
        assert "🟢" in result

    def test_returns_inactive_when_flag_false(self) -> None:
        """Returns inactive status when flag is False."""
        result = BasicInfoPrinter._format_exchange_status_line("Test Label", False)

        assert "INACTIVE" in result
        assert "🔴" in result

    def test_includes_label_in_output(self) -> None:
        """Includes label in formatted output."""
        result = BasicInfoPrinter._format_exchange_status_line("My Custom Label", True)

        assert "My Custom Label" in result


class TestPrintPriceInfo:
    """Tests for print_price_info method."""

    def test_prints_btc_price(self) -> None:
        """Prints BTC price when available."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_price_info(50000.0, None)

        assert any("50,000" in str(line) for line in emitted)

    def test_prints_eth_price(self) -> None:
        """Prints ETH price when available."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_price_info(None, 3000.0)

        assert any("3,000" in str(line) for line in emitted)

    def test_prints_na_when_btc_unavailable(self) -> None:
        """Prints N/A when BTC price unavailable."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_price_info(None, 3000.0)

        assert any("N/A" in str(line) and "BTC" in str(line) for line in emitted)

    def test_prints_na_when_eth_unavailable(self) -> None:
        """Prints N/A when ETH price unavailable."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_price_info(50000.0, None)

        assert any("N/A" in str(line) and "ETH" in str(line) for line in emitted)


class TestPrintWeatherSection:
    """Tests for print_weather_section method."""

    def test_does_nothing_when_no_lines(self) -> None:
        """Does nothing when weather_lines is empty."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_weather_section([])

        assert len(emitted) == 0

    def test_prints_all_weather_lines(self) -> None:
        """Prints all weather lines."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_weather_section(["Line 1", "Line 2", "Line 3"])

        assert "Line 1" in emitted
        assert "Line 2" in emitted
        assert "Line 3" in emitted


class TestPrintManagedServices:
    """Tests for print_managed_services method."""

    def test_returns_counts(self) -> None:
        """Returns healthy and total counts."""
        process_manager = MagicMock()
        process_manager.services = ["service1", "service2"]
        info1 = MagicMock()
        info1.status = ProcessStatus.RUNNING
        info2 = MagicMock()
        info2.status = ProcessStatus.STOPPED
        process_manager.process_info = {"service1": info1, "service2": info2}
        service_status_formatter = MagicMock()
        service_status_formatter.build_service_status_line.return_value = "status line"
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        printer._emit_status_line = lambda x="": None

        healthy, total = printer.print_managed_services({}, {})

        assert healthy == 1
        assert total == 2

    def test_prints_service_lines(self) -> None:
        """Prints status line for each service."""
        process_manager = MagicMock()
        process_manager.services = ["service1"]
        info = MagicMock()
        info.status = ProcessStatus.RUNNING
        process_manager.process_info = {"service1": info}
        service_status_formatter = MagicMock()
        service_status_formatter.build_service_status_line.return_value = "  🟢 service1 - Active"
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_managed_services({}, {})

        assert "  🟢 service1 - Active" in emitted

    def test_handles_missing_process_info(self) -> None:
        """Handles services without process info."""
        process_manager = MagicMock()
        process_manager.services = ["service1"]
        process_manager.process_info = {}
        service_status_formatter = MagicMock()
        service_status_formatter.build_service_status_line.return_value = "status line"
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        printer._emit_status_line = lambda x="": None

        healthy, total = printer.print_managed_services({}, {})

        assert healthy == 0
        assert total == 1


class TestPrintMonitorService:
    """Tests for print_monitor_service method."""

    def test_prints_monitor_line(self) -> None:
        """Prints monitor service status line."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        printer.monitor_printer.build_monitor_status_line = MagicMock(return_value="  🟢 monitor - Active")
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_monitor_service({})

        assert "  🟢 monitor - Active" in emitted

    def test_does_nothing_when_no_line(self) -> None:
        """Does nothing when monitor returns empty line."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()
        printer = BasicInfoPrinter(process_manager, service_status_formatter)
        printer.monitor_printer.build_monitor_status_line = MagicMock(return_value="")
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_monitor_service({})

        assert len(emitted) == 0
