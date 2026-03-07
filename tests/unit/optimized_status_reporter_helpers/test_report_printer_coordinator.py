"""Unit tests for report_printer_coordinator."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.optimized_status_reporter_helpers.report_printer_coordinator import (
    ReportPrinterCoordinator,
)


class TestReportPrinterCoordinator:
    """Tests for ReportPrinterCoordinator."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for the coordinator."""
        return {
            "emit_func": Mock(),
            "section_printer": Mock(),
            "service_printer": Mock(),
            "metrics_printer": Mock(),
            "weather_generator": Mock(),
            "process_manager": Mock(),
        }

    @pytest.fixture
    def coordinator(self, mock_dependencies):
        """Return a ReportPrinterCoordinator instance with mocked dependencies."""
        return ReportPrinterCoordinator(**mock_dependencies)

    @pytest.mark.asyncio
    async def test_print_status_report(self, coordinator, mock_dependencies):
        """Test print_status_report method calls all sub-printers and emits correctly."""
        mock_dependencies["process_manager"].get_managed_processes.return_value = []
        mock_dependencies["service_printer"].print_managed_services.return_value = (
            2,
            3,
        )  # healthy, total

        status_data = {
            "kalshi_market_status": {},
            "tracker_status": {},
            "log_activity": {},
        }

        with patch("common.time_utils.get_current_utc") as mock_get_current_utc:
            mock_get_current_utc.return_value.strftime.return_value = "2023-01-01 12:00:00"

            await coordinator.print_status_report(status_data)

            # Assert emit_func calls
            assert mock_dependencies["emit_func"].call_count == 5

            # Assert section_printer calls
            mock_dependencies["section_printer"].print_exchange_info.assert_called_once_with("2023-01-01 12:00:00", {})
            mock_dependencies["section_printer"].print_price_info.assert_called_once_with(status_data)
            mock_dependencies["section_printer"].print_weather_info.assert_called_once_with(
                status_data, mock_dependencies["weather_generator"]
            )

            # Assert service_printer calls
            mock_dependencies["service_printer"].print_managed_services.assert_called_once_with(
                mock_dependencies["process_manager"], {}, {}
            )
            mock_dependencies["service_printer"].print_monitor_service.assert_called_once_with(mock_dependencies["process_manager"], {})

            # Assert metrics_printer calls
            mock_dependencies["metrics_printer"].print_all_health_sections.assert_called_once_with(status_data)
            mock_dependencies["section_printer"].print_tracker_status_section.assert_called_once()
