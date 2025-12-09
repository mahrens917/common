"""Tests for monitor service printer module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.common.health.log_activity_monitor import LogActivity, LogActivityStatus
from src.common.monitoring import ProcessStatus
from src.common.optimized_status_reporter_helpers.monitor_service_printer import (
    MonitorServicePrinter,
)


class TestMonitorServicePrinter:
    """Tests for MonitorServicePrinter class."""

    def test_init_stores_dependencies(self) -> None:
        """Stores process_manager and service_status_formatter."""
        process_manager = MagicMock()
        service_status_formatter = MagicMock()

        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        assert printer.process_manager == process_manager
        assert printer.service_status_formatter == service_status_formatter


class TestBuildMonitorStatusLine:
    """Tests for build_monitor_status_line method."""

    def test_returns_empty_when_no_monitor_info(self) -> None:
        """Returns empty string when monitor process info missing."""
        process_manager = MagicMock()
        process_manager.process_info = {}
        service_status_formatter = MagicMock()
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert result == ""

    def test_returns_green_emoji_when_running(self) -> None:
        """Returns green emoji when monitor is running."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.RUNNING
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "🟢" in result

    def test_returns_red_emoji_when_not_running(self) -> None:
        """Returns red emoji when monitor is not running."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.STOPPED
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "🔴" in result

    def test_returns_yellow_emoji_when_running_with_error(self) -> None:
        """Returns yellow emoji when running but has error activity."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.RUNNING
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)
        activity = MagicMock()
        activity.status = LogActivityStatus.ERROR

        result = printer.build_monitor_status_line({"monitor": activity})

        assert "🟡" in result

    def test_shows_active_when_running(self) -> None:
        """Shows 'Active' status when running."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.RUNNING
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "Active" in result

    def test_shows_status_value_when_not_running(self) -> None:
        """Shows formatted status value when not running."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.STOPPED
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "Stopped" in result

    def test_shows_unknown_when_no_status(self) -> None:
        """Shows 'Unknown' when status is None."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = None
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "Unknown" in result

    def test_includes_age_when_available(self) -> None:
        """Includes age information in parentheses."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.RUNNING
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = "5m ago"
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "(5m ago)" in result

    def test_includes_resource_info_when_available(self) -> None:
        """Includes resource usage information."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.RUNNING
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = (
            " [CPU: 5%, MEM: 10MB]"
        )
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "[CPU: 5%, MEM: 10MB]" in result

    def test_includes_monitor_label(self) -> None:
        """Includes 'monitor' label in output."""
        process_manager = MagicMock()
        info = MagicMock()
        info.status = ProcessStatus.RUNNING
        process_manager.process_info = {"monitor": info}
        service_status_formatter = MagicMock()
        service_status_formatter.log_activity_formatter.format_age_only.return_value = ""
        service_status_formatter.resource_tracker.get_process_resource_usage.return_value = ""
        printer = MonitorServicePrinter(process_manager, service_status_formatter)

        result = printer.build_monitor_status_line({})

        assert "monitor" in result
