"""Tests for alerter_helpers.load_charts_sender module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alerter_helpers.load_charts_sender import LoadChartsSender
from common.chart_generator import InsufficientDataError, ProgressNotificationError
from common.price_path_calculator import PricePathComputationError


class TestLoadChartsSenderInit:
    """Tests for LoadChartsSender initialization."""

    def test_stores_dependencies(self) -> None:
        """Test initialization stores dependencies."""
        mock_generator = MagicMock()
        mock_send_image = MagicMock()
        mock_send_alert = MagicMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)

        assert sender.chart_generator == mock_generator
        assert sender.send_chart_image == mock_send_image
        assert sender.send_alert == mock_send_alert


class TestLoadChartsSenderSendLoadCharts:
    """Tests for send_load_charts method."""

    @pytest.mark.asyncio
    async def test_sends_charts_successfully(self) -> None:
        """Test sends charts successfully."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.return_value = ["/path/chart1.png", "/path/chart2.png"]
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)

        with patch("common.alerter_helpers.load_charts_sender.ChartBatchSender") as mock_batch_sender_class:
            mock_batch_sender = MagicMock()
            mock_batch_sender.send_charts_batch = AsyncMock(return_value=2)
            mock_batch_sender_class.return_value = mock_batch_sender

            result = await sender.send_load_charts(hours=24)

        assert result is True
        mock_generator.generate_load_charts.assert_called_once_with(hours=24)

    @pytest.mark.asyncio
    async def test_returns_false_when_no_charts(self) -> None:
        """Test returns False when no charts generated."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.return_value = []
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_none_charts(self) -> None:
        """Test returns False when None charts returned."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.return_value = None
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_partial_send(self) -> None:
        """Test returns False when not all charts sent."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.return_value = ["/path/chart1.png", "/path/chart2.png"]
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)

        with patch("common.alerter_helpers.load_charts_sender.ChartBatchSender") as mock_batch_sender_class:
            mock_batch_sender = MagicMock()
            mock_batch_sender.send_charts_batch = AsyncMock(return_value=1)  # Only 1 of 2
            mock_batch_sender_class.return_value = mock_batch_sender

            result = await sender.send_load_charts()

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_insufficient_data_error(self) -> None:
        """Test handles InsufficientDataError."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.side_effect = InsufficientDataError("Not enough data")
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False
        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args[0][0]
        assert "Cannot generate charts" in call_args

    @pytest.mark.asyncio
    async def test_handles_price_path_computation_error(self) -> None:
        """Test handles PricePathComputationError."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.side_effect = PricePathComputationError("Computation failed")
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False
        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args[0][0]
        assert "Error generating charts" in call_args

    @pytest.mark.asyncio
    async def test_handles_progress_notification_error(self) -> None:
        """Test handles ProgressNotificationError."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.side_effect = ProgressNotificationError("Notification failed")
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False
        mock_send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self) -> None:
        """Test handles RuntimeError."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.side_effect = RuntimeError("Runtime failure")
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False
        mock_send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_value_error(self) -> None:
        """Test handles ValueError."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.side_effect = ValueError("Invalid value")
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False
        mock_send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_os_error(self) -> None:
        """Test handles OSError."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.side_effect = OSError("File system error")
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)
        result = await sender.send_load_charts()

        assert result is False
        mock_send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_custom_hours(self) -> None:
        """Test uses custom hours parameter."""
        mock_generator = AsyncMock()
        mock_generator.generate_load_charts.return_value = ["/path/chart.png"]
        mock_send_image = AsyncMock()
        mock_send_alert = AsyncMock()

        sender = LoadChartsSender(mock_generator, mock_send_image, mock_send_alert)

        with patch("common.alerter_helpers.load_charts_sender.ChartBatchSender") as mock_batch_sender_class:
            mock_batch_sender = MagicMock()
            mock_batch_sender.send_charts_batch = AsyncMock(return_value=1)
            mock_batch_sender_class.return_value = mock_batch_sender

            await sender.send_load_charts(hours=48)

        mock_generator.generate_load_charts.assert_called_once_with(hours=48)
