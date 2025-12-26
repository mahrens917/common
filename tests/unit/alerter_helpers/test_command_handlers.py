"""Tests for alerter command handlers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.alerter_helpers.command_handlers import (
    ChartGeneratorProtocol,
    HelpCommandHandler,
    LoadCommandHandler,
    PnlCommandHandler,
    PriceCommandHandler,
    TempCommandHandler,
)
from common.alerting import AlertSeverity
from common.chart_generator import InsufficientDataError, ProgressNotificationError
from common.price_path_calculator import PricePathComputationError


class TestHelpCommandHandler:
    """Test HelpCommandHandler."""

    @pytest.mark.asyncio
    async def test_handle_sends_help_text(self):
        """Test /help command sends all available commands."""
        send_alert = AsyncMock()
        handler = HelpCommandHandler()

        await handler.handle(send_alert)

        send_alert.assert_called_once()
        call_args = send_alert.call_args
        help_text = call_args[0][0]

        # Verify all commands are in the help text
        assert "/pnl" in help_text
        assert "/markets" in help_text
        assert "/status" in help_text
        assert "/jobs" in help_text
        assert "/temp" in help_text
        assert "/price" in help_text
        assert "/surface" in help_text
        assert "/trade" in help_text
        assert "/load" in help_text
        assert "/ping" in help_text
        assert "/restart" in help_text
        assert "/help" in help_text

        assert call_args[1]["alert_type"] == "help_response"


class TestLoadCommandHandler:
    """Test LoadCommandHandler."""

    @pytest.fixture
    def chart_generator_mock(self):
        """Create a mock chart generator."""
        mock = AsyncMock(spec=ChartGeneratorProtocol)
        return mock

    @pytest.mark.asyncio
    async def test_handle_no_chart_generator(self, chart_generator_mock):
        """Test /load command when chart generator is unavailable."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()
        handler = LoadCommandHandler(None, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once_with("❌ Chart generator unavailable; cannot produce load charts")

    @pytest.mark.asyncio
    async def test_handle_generates_and_sends_charts(self, chart_generator_mock):
        """Test /load command successfully generates and sends charts."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_paths = {
            "system": "/path/to/system_chart.png",
            "cpu": "/path/to/cpu_chart.png",
        }
        chart_generator_mock.generate_load_charts.return_value = chart_paths

        handler = LoadCommandHandler(chart_generator_mock, send_alert, send_chart_image)

        with patch("common.alerter_helpers.chart_batch_sender.ChartBatchSender") as batch_sender_mock:
            batch_sender_instance = AsyncMock()
            batch_sender_instance.send_charts_batch.return_value = 2
            batch_sender_mock.return_value = batch_sender_instance

            await handler.handle({})

        chart_generator_mock.generate_load_charts.assert_called_once_with(hours=24)
        send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_insufficient_data_error(self, chart_generator_mock):
        """Test /load command with insufficient data."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_generator_mock.generate_load_charts.side_effect = InsufficientDataError("No data")

        handler = LoadCommandHandler(chart_generator_mock, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once_with("❌ Insufficient data for load charts")

    @pytest.mark.asyncio
    async def test_handle_price_path_computation_error(self, chart_generator_mock):
        """Test /load command with price path computation error."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_generator_mock.generate_load_charts.side_effect = PricePathComputationError("Computation failed")

        handler = LoadCommandHandler(chart_generator_mock, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once_with("❌ Failed to generate load charts")

    @pytest.mark.asyncio
    async def test_handle_progress_notification_error(self, chart_generator_mock):
        """Test /load command with progress notification error."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_generator_mock.generate_load_charts.side_effect = ProgressNotificationError("Progress failed")

        handler = LoadCommandHandler(chart_generator_mock, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once_with("❌ Failed to generate load charts")

    @pytest.mark.asyncio
    async def test_handle_no_charts_generated(self, chart_generator_mock):
        """Test /load command when no charts are generated."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_generator_mock.generate_load_charts.return_value = {}

        handler = LoadCommandHandler(chart_generator_mock, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once_with("❌ No load charts generated")


class TestPnlCommandHandler:
    """Test PnlCommandHandler."""

    @pytest.mark.asyncio
    async def test_handle_no_date_specified(self):
        """Test /pnl command without date uses current date."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        pnl_reporter = AsyncMock()
        pnl_reporter.build_full_report.return_value = ("Summary text", {})

        ensure_pnl_reporter = AsyncMock(return_value=pnl_reporter)

        handler = PnlCommandHandler(
            pnl_reporter=pnl_reporter,
            chart_generator=None,
            send_alert_callback=send_alert,
            send_chart_image_callback=send_chart_image,
            ensure_pnl_reporter_callback=ensure_pnl_reporter,
        )

        await handler.handle({"text": "/pnl"})

        pnl_reporter.build_full_report.assert_called_once_with(None)
        send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_with_valid_date(self):
        """Test /pnl command with valid date."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        pnl_reporter = AsyncMock()
        target_date = date(2024, 1, 15)
        pnl_reporter.build_full_report.return_value = ("Summary text", {})

        ensure_pnl_reporter = AsyncMock(return_value=pnl_reporter)

        handler = PnlCommandHandler(
            pnl_reporter=pnl_reporter,
            chart_generator=None,
            send_alert_callback=send_alert,
            send_chart_image_callback=send_chart_image,
            ensure_pnl_reporter_callback=ensure_pnl_reporter,
        )

        await handler.handle({"text": "/pnl 2024-01-15"})

        pnl_reporter.build_full_report.assert_called_once_with(target_date)

    @pytest.mark.asyncio
    async def test_handle_with_invalid_date(self):
        """Test /pnl command with invalid date format."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        pnl_reporter = AsyncMock()
        ensure_pnl_reporter = AsyncMock(return_value=pnl_reporter)

        handler = PnlCommandHandler(
            pnl_reporter=pnl_reporter,
            chart_generator=None,
            send_alert_callback=send_alert,
            send_chart_image_callback=send_chart_image,
            ensure_pnl_reporter_callback=ensure_pnl_reporter,
        )

        await handler.handle({"text": "/pnl invalid-date"})

        send_alert.assert_called_once()
        call_args = send_alert.call_args[0]
        assert "Invalid date format" in call_args[0]
        assert send_alert.call_args[1]["severity"] == AlertSeverity.WARNING

    @pytest.mark.asyncio
    async def test_handle_with_chart_generator(self):
        """Test /pnl command with chart generation."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        pnl_reporter = AsyncMock()
        pnl_reporter.build_full_report.return_value = ("Summary text", {"data": "payload"})

        chart_generator = AsyncMock(spec=ChartGeneratorProtocol)
        chart_generator.generate_pnl_charts.return_value = ["/path/chart1.png", "/path/chart2.png"]

        ensure_pnl_reporter = AsyncMock(return_value=pnl_reporter)

        handler = PnlCommandHandler(
            pnl_reporter=pnl_reporter,
            chart_generator=chart_generator,
            send_alert_callback=send_alert,
            send_chart_image_callback=send_chart_image,
            ensure_pnl_reporter_callback=ensure_pnl_reporter,
        )

        await handler.handle({"text": "/pnl"})

        chart_generator.generate_pnl_charts.assert_called_once_with({"data": "payload"})
        assert send_chart_image.call_count == 2
        assert chart_generator.cleanup_single_chart_file.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_insufficient_data_for_charts(self):
        """Test /pnl command with insufficient data for charts."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        pnl_reporter = AsyncMock()
        pnl_reporter.build_full_report.return_value = ("Summary text", {})

        chart_generator = AsyncMock(spec=ChartGeneratorProtocol)
        chart_generator.generate_pnl_charts.side_effect = InsufficientDataError("No data")

        ensure_pnl_reporter = AsyncMock(return_value=pnl_reporter)

        handler = PnlCommandHandler(
            pnl_reporter=pnl_reporter,
            chart_generator=chart_generator,
            send_alert_callback=send_alert,
            send_chart_image_callback=send_chart_image,
            ensure_pnl_reporter_callback=ensure_pnl_reporter,
        )

        await handler.handle({"text": "/pnl"})

        # First alert for summary, second for unavailable charts
        assert send_alert.call_count == 2
        assert "unavailable" in send_alert.call_args_list[1][0][0].lower()


class TestTempCommandHandler:
    """Test TempCommandHandler."""

    @pytest.mark.asyncio
    async def test_handle_no_chart_generator(self):
        """Test /temp command when chart generator is unavailable."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()
        handler = TempCommandHandler(None, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once_with("❌ Chart generator unavailable; cannot generate weather charts")

    @pytest.mark.asyncio
    async def test_handle_generates_and_sends_weather_charts(self):
        """Test /temp command generates and sends weather charts."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_generator = AsyncMock(spec=ChartGeneratorProtocol)
        chart_generator.generate_weather_charts.return_value = [
            "/path/temp_chart1.png",
            "/path/temp_chart2.png",
        ]

        handler = TempCommandHandler(chart_generator, send_alert, send_chart_image)

        await handler.handle({})

        chart_generator.generate_weather_charts.assert_called_once()
        assert send_chart_image.call_count == 2
        assert chart_generator.cleanup_single_chart_file.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_insufficient_weather_data(self):
        """Test /temp command with insufficient weather data."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_generator = AsyncMock(spec=ChartGeneratorProtocol)
        chart_generator.generate_weather_charts.side_effect = InsufficientDataError("No weather data")

        handler = TempCommandHandler(chart_generator, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once_with("⚪ Weather data unavailable")

    @pytest.mark.asyncio
    async def test_handle_weather_chart_error(self):
        """Test /temp command with chart generation error."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        chart_generator = AsyncMock(spec=ChartGeneratorProtocol)
        chart_generator.generate_weather_charts.side_effect = PricePathComputationError("Chart error")

        handler = TempCommandHandler(chart_generator, send_alert, send_chart_image)

        await handler.handle({})

        send_alert.assert_called_once()
        call_args = send_alert.call_args[0]
        assert "Failed" in call_args[0]


class TestPriceCommandHandler:
    """Test PriceCommandHandler."""

    @pytest.mark.asyncio
    async def test_handle_generates_price_charts_for_both_currencies(self):
        """Test /price command generates charts for BTC and ETH."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        handler = PriceCommandHandler(send_alert, send_chart_image)

        with patch.object(handler, "_generate_price_chart", new_callable=AsyncMock) as mock_generate:
            await handler.handle({})

        # Should generate charts for BTC and ETH, with short and long horizons
        assert mock_generate.call_count == 4

    def test_build_tail_specs(self):
        """Test price tail spec generation."""
        handler = PriceCommandHandler(AsyncMock(), AsyncMock())

        tails = handler._build_tail_specs()

        assert len(tails) == 2
        # Short horizon
        assert tails[0][0] == "short"
        assert tails[0][1] == 12.0 / 24.0
        assert tails[0][2] == 12

        # Long horizon
        assert tails[1][0] == "long"
        assert tails[1][1] == 365.0

    @pytest.mark.asyncio
    async def test_generate_price_chart_success(self):
        """Test successful price chart generation."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        handler = PriceCommandHandler(send_alert, send_chart_image)

        with patch("common.alerter_helpers.command_handlers.ChartGenerator") as chart_gen_mock:
            chart_instance = AsyncMock(spec=ChartGeneratorProtocol)
            chart_instance.generate_price_chart_with_path.return_value = "/path/btc_short.png"
            chart_gen_mock.return_value = chart_instance

            await handler._generate_price_chart("BTC", "short", 0.5, 12)

        send_chart_image.assert_called_once_with("/path/btc_short.png", "")

    @pytest.mark.asyncio
    async def test_generate_price_chart_insufficient_data(self):
        """Test price chart generation with insufficient data."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        handler = PriceCommandHandler(send_alert, send_chart_image)

        with patch("common.alerter_helpers.command_handlers.ChartGenerator") as chart_gen_mock:
            chart_instance = AsyncMock(spec=ChartGeneratorProtocol)
            chart_instance.generate_price_chart_with_path.side_effect = InsufficientDataError("No data")
            chart_gen_mock.return_value = chart_instance

            await handler._generate_price_chart("BTC", "short", 0.5, 12)

        send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_price_chart_computation_error(self):
        """Test price chart generation with computation error."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        handler = PriceCommandHandler(send_alert, send_chart_image)

        with patch("common.alerter_helpers.command_handlers.ChartGenerator") as chart_gen_mock:
            chart_instance = AsyncMock(spec=ChartGeneratorProtocol)
            chart_instance.generate_price_chart_with_path.side_effect = PricePathComputationError("Error")
            chart_gen_mock.return_value = chart_instance

            await handler._generate_price_chart("ETH", "long", 365.0, 365)

        send_alert.assert_called_once()
        call_args = send_alert.call_args[0]
        assert "Failed" in call_args[0]
        assert "ETH" in call_args[0]

    @pytest.mark.asyncio
    async def test_generate_price_chart_no_cleanup_on_no_path(self):
        """Test price chart cleanup not called when no path generated."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        handler = PriceCommandHandler(send_alert, send_chart_image)

        with patch("common.alerter_helpers.command_handlers.ChartGenerator") as chart_gen_mock:
            chart_instance = AsyncMock(spec=ChartGeneratorProtocol)
            chart_instance.generate_price_chart_with_path.return_value = None
            chart_gen_mock.return_value = chart_instance

            # Should not raise exception
            await handler._generate_price_chart("BTC", "short", 0.5, 12)

        # Cleanup should not be called since path is None
        chart_instance.cleanup_single_chart_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_price_chart_cleanup_failure(self):
        """Test price chart cleanup failure is handled gracefully."""
        send_alert = AsyncMock()
        send_chart_image = AsyncMock()

        handler = PriceCommandHandler(send_alert, send_chart_image)

        with patch("common.alerter_helpers.command_handlers.ChartGenerator") as chart_gen_mock:
            chart_instance = AsyncMock(spec=ChartGeneratorProtocol)
            chart_instance.generate_price_chart_with_path.return_value = "/path/chart.png"
            chart_instance.cleanup_single_chart_file.side_effect = OSError("Cleanup failed")
            chart_gen_mock.return_value = chart_instance

            # Should not raise exception
            await handler._generate_price_chart("BTC", "short", 0.5, 12)

        # Should have attempted cleanup
        chart_instance.cleanup_single_chart_file.assert_called_once_with("/path/chart.png")
