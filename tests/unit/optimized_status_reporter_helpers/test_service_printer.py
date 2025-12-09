"""Unit tests for service_printer."""

from unittest.mock import Mock, patch

import pytest

from src.common.health.log_activity_monitor import LogActivity, LogActivityStatus
from src.common.monitoring import ProcessStatus
from src.common.optimized_status_reporter_helpers.service_printer import (
    ServicePrinter,
)

DEFAULT_SERVICE_PRINTER_HEALTHY_COUNT = 1
DEFAULT_SERVICE_PRINTER_TOTAL_COUNT = 2


class TestServicePrinter:
    """Tests for ServicePrinter."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for ServicePrinter."""
        return {
            "emit_func": Mock(),
            "resource_tracker": Mock(),
            "log_formatter": Mock(),
            "bool_or_default_func": Mock(),
        }

    @pytest.fixture
    def printer(self, mock_dependencies):
        """ServicePrinter instance with mocked dependencies."""
        return ServicePrinter(**mock_dependencies)

    @pytest.fixture
    def mock_process_manager(self):
        """Mock process manager with services and process_info."""
        pm = Mock()
        pm.services = ["service_A", "service_B"]
        pm.process_info = {
            "service_A": Mock(name="service_A", pid=123, status=ProcessStatus.RUNNING),
            "service_B": Mock(name="service_B", pid=456, status=ProcessStatus.STOPPED),
            "monitor": Mock(name="monitor", pid=789, status=ProcessStatus.RUNNING),
        }
        return pm

    @patch(
        "src.common.optimized_status_reporter_helpers.service_printer.get_status_emoji",
        return_value="✅",
    )
    @patch(
        "src.common.optimized_status_reporter_helpers.service_printer.resolve_service_status",
        return_value="Running",
    )
    def test_print_managed_services(
        self,
        _mock_resolve_service_status,
        _mock_get_status_emoji,
        printer,
        mock_process_manager,
        mock_dependencies,
    ):
        """Test _print_managed_services prints status for all services."""
        mock_dependencies["log_formatter"].format_age_only.return_value = ""
        mock_dependencies["resource_tracker"].get_process_resource_usage.return_value = ""

        healthy_count, total_count = printer.print_managed_services(mock_process_manager, {}, {})

        assert healthy_count == DEFAULT_SERVICE_PRINTER_HEALTHY_COUNT  # service_A is running
        assert total_count == DEFAULT_SERVICE_PRINTER_TOTAL_COUNT  # service_A, service_B
        assert mock_dependencies["emit_func"].call_count == 2
        mock_dependencies["emit_func"].assert_any_call("  ✅ service_A - Running")
        mock_dependencies["emit_func"].assert_any_call(
            "  ✅ service_B - Running"
        )  # Mocked resolve_service_status

    def test_print_managed_services_no_services(self, printer, mock_process_manager):
        """Test _print_managed_services handles no services."""
        mock_process_manager.services = []
        healthy_count, total_count = printer.print_managed_services(mock_process_manager, {}, {})
        assert healthy_count == 0
        assert total_count == 0
        printer._emit.assert_not_called()

    @patch(
        "src.common.optimized_status_reporter_helpers.service_printer.get_status_emoji",
        return_value="✅",
    )
    def test_print_monitor_service_no_monitor_info(
        self, _mock_get_status_emoji, printer, mock_process_manager
    ):
        """Test _print_monitor_service does nothing if no monitor info."""
        mock_process_manager.process_info = {}  # No monitor info
        printer.print_monitor_service(mock_process_manager, {})
        printer._emit.assert_not_called()

    @patch(
        "src.common.optimized_status_reporter_helpers.service_printer.get_status_emoji",
        return_value="✅",
    )
    def test_print_monitor_service_running(
        self, _mock_get_status_emoji, printer, mock_process_manager, mock_dependencies
    ):
        """Test _print_monitor_service prints running status."""
        mock_dependencies["resource_tracker"].get_process_resource_usage.return_value = " RAM: 1.5%"
        mock_dependencies["log_formatter"].format_log_activity_short.return_value = (
            " (Last log: 10s ago)"
        )

        printer.print_monitor_service(
            mock_process_manager, {"monitor": LogActivity(LogActivityStatus.RECENT)}
        )
        printer._emit.assert_called_once_with(
            "  ✅ monitor - Running - RAM: 1.5% -  (Last log: 10s ago)"
        )

    @patch(
        "src.common.optimized_status_reporter_helpers.service_printer.get_status_emoji",
        return_value="❌",
    )
    def test_print_monitor_service_stopped(
        self, _mock_get_status_emoji, printer, mock_process_manager, mock_dependencies
    ):
        """Test _print_monitor_service prints stopped status."""
        mock_process_manager.process_info["monitor"].status = ProcessStatus.STOPPED
        mock_dependencies["resource_tracker"].get_process_resource_usage.return_value = ""
        mock_dependencies["log_formatter"].format_log_activity_short.return_value = ""

        printer.print_monitor_service(mock_process_manager, {})
        printer._emit.assert_called_once_with("  ❌ monitor - Stopped")

    @patch(
        "src.common.optimized_status_reporter_helpers.service_printer.get_status_emoji",
        return_value="❓",
    )
    def test_print_monitor_service_unknown_status(
        self, _mock_get_status_emoji, printer, mock_process_manager, mock_dependencies
    ):
        """Test _print_monitor_service prints unknown status."""
        mock_process_manager.process_info["monitor"].status = None  # Simulate unknown status
        mock_dependencies["resource_tracker"].get_process_resource_usage.return_value = ""
        mock_dependencies["log_formatter"].format_log_activity_short.return_value = ""
        printer.print_monitor_service(mock_process_manager, {})
        printer._emit.assert_called_once_with("  ❓ monitor - Unknown")

    def test_build_service_status_line_full_info(self, printer, mock_dependencies):
        """Test _build_service_status_line with full info."""
        mock_dependencies["log_formatter"].format_age_only.return_value = "10s ago"
        mock_dependencies["resource_tracker"].get_process_resource_usage.return_value = " RAM: 2.0%"

        with patch(
            "src.common.optimized_status_reporter_helpers.service_printer.get_status_emoji",
            return_value="🟢",
        ):
            with patch(
                "src.common.optimized_status_reporter_helpers.service_printer.resolve_service_status",
                return_value="Service Running",
            ):
                line = printer._build_service_status_line(
                    "test_service", Mock(), True, {}, LogActivity(LogActivityStatus.RECENT)
                )
                assert line == "  🟢 test_service - Service Running (10s ago) RAM: 2.0%"

    def test_build_service_status_line_no_age_no_resource(self, printer, mock_dependencies):
        """Test _build_service_status_line with no age or resource info."""
        mock_dependencies["log_formatter"].format_age_only.return_value = ""
        mock_dependencies["resource_tracker"].get_process_resource_usage.return_value = ""

        with patch(
            "src.common.optimized_status_reporter_helpers.service_printer.get_status_emoji",
            return_value="🟢",
        ):
            with patch(
                "src.common.optimized_status_reporter_helpers.service_printer.resolve_service_status",
                return_value="Service Running",
            ):
                line = printer._build_service_status_line(
                    "test_service", Mock(), True, {}, LogActivity(LogActivityStatus.RECENT)
                )
                assert line == "  🟢 test_service - Service Running"
