"""Unit tests for metrics_section_printer."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from common.optimized_status_reporter_helpers.metrics_section_printer import (
    MetricsSectionPrinter,
)


class TestMetricsSectionPrinter:
    """Tests for MetricsSectionPrinter."""

    @pytest.fixture
    def data_coercion(self):
        """Mocked data coercion helpers."""
        mock = Mock()
        mock.int_or_default.side_effect = lambda value, default=0: (
            default if value is None else value
        )
        mock.coerce_mapping.side_effect = lambda value: value or {}
        mock.string_or_default.side_effect = lambda value, default="Unknown": value or default
        mock.bool_or_default.side_effect = lambda value, default=False: (
            default if value is None else value
        )
        return mock

    @pytest.fixture
    def printer(self, data_coercion):
        """MetricsSectionPrinter instance with captured output."""
        printer = MetricsSectionPrinter(data_coercion)
        printer._emitted = []
        printer._emit_status_line = lambda line="": printer._emitted.append(line)
        return printer

    def test_print_message_metrics_section_handles_inactive_exchange(self, printer, data_coercion):
        """Verifies Kalshi inactive path and message formatting."""
        data_coercion.coerce_mapping.return_value = {"trading_active": False}
        printer.print_message_metrics_section(
            {
                "deribit_messages_60s": 12,
                "kalshi_market_status": {"trading_active": False},
                "cfb_messages_60s": 3,
            }
        )

        assert printer._emitted[:3] == [
            "",
            "📈 Message Metrics (Past 60 Seconds):",
            "  🟢 Deribit Messages - 12",
        ]
        assert "exchange inactive" in printer._emitted[3]
        assert printer._emitted[-1] == "  🟢 CFB Messages - 3"

    def test_print_message_metrics_section_handles_active_exchange(self, printer, data_coercion):
        """Verifies Kalshi active path uses message totals."""
        data_coercion.coerce_mapping.return_value = {"trading_active": True}
        printer.print_message_metrics_section(
            {
                "deribit_messages_60s": 5,
                "kalshi_market_status": {"trading_active": True},
                "kalshi_messages_60s": 7,
                "cfb_messages_60s": 9,
            }
        )

        assert "  🟢 Kalshi Messages - 7" in printer._emitted
        assert printer._emitted[-1] == "  🟢 CFB Messages - 9"

    @patch("common.optimized_status_reporter_helpers.metrics_section_printer.get_weather_settings")
    def test_print_weather_metrics_section_disables_asos_when_off(
        self, mock_get_weather_settings, printer, data_coercion
    ):
        """ASOS disabled path surfaces correct line."""
        mock_get_weather_settings.return_value = SimpleNamespace(
            sources=SimpleNamespace(asos_source="off")
        )

        printer.print_weather_metrics_section({"metar_messages_65m": 4})

        assert printer._emitted[0] == ""
        assert "DISABLED" in printer._emitted[2]
        assert printer._emitted[-1] == "  🟢 METAR Temperature Changes - 4"

    @patch("common.optimized_status_reporter_helpers.metrics_section_printer.get_weather_settings")
    def test_print_weather_metrics_section_prints_asos_and_metar(
        self, mock_get_weather_settings, printer, data_coercion
    ):
        """ASOS enabled path prints both metrics."""
        mock_get_weather_settings.return_value = SimpleNamespace(
            sources=SimpleNamespace(asos_source="on")
        )
        data_coercion.int_or_default.side_effect = [8, 10]

        printer.print_weather_metrics_section({"asos_messages_65m": 8, "metar_messages_65m": 10})

        assert "ASOS Temperature Changes - 8" in printer._emitted[2]
        assert printer._emitted[-1] == "  🟢 METAR Temperature Changes - 10"

    def test_print_tracker_status_section_handles_missing_and_disabled(
        self, printer, data_coercion
    ):
        """Tracker status section covers missing info and disabled override."""
        printer.print_tracker_status_section({})
        assert printer._emitted[-2] == "  🔴 Tracker status unavailable"
        printer._emitted.clear()

        data_coercion.string_or_default.return_value = "Running"
        data_coercion.bool_or_default.side_effect = [False, False]
        printer.print_tracker_status_section(
            {"status_summary": "Running", "running": False, "enabled": False}
        )

        assert printer._emitted[-2] == "  🔴 Stopped | Disabled"

    def test_print_tracker_status_section_prints_summary(self, printer, data_coercion):
        """Tracker status section prints supplied summary when enabled."""
        data_coercion.string_or_default.return_value = "All good"
        data_coercion.bool_or_default.side_effect = [True, True]

        printer.print_tracker_status_section(
            {"status_summary": "All good", "running": True, "enabled": True}
        )

        assert printer._emitted[-2] == "  All good"
