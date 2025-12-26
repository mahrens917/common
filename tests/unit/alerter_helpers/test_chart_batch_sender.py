"""Tests for chart_batch_sender module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.alerter_helpers.chart_batch_sender import ChartBatchSender


@pytest.fixture
def mock_chart_generator() -> MagicMock:
    """Create a mock chart generator."""
    generator = MagicMock()
    generator.cleanup_single_chart_file = MagicMock()
    return generator


@pytest.fixture
def mock_send_chart() -> AsyncMock:
    """Create a mock send chart callback."""
    return AsyncMock(return_value=True)


@pytest.fixture
def mock_send_alert() -> AsyncMock:
    """Create a mock send alert callback."""
    return AsyncMock()


class TestChartBatchSender:
    """Tests for ChartBatchSender class."""

    def test_init(
        self,
        mock_chart_generator: MagicMock,
        mock_send_chart: AsyncMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test ChartBatchSender initialization."""
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)

        assert sender.chart_generator is mock_chart_generator
        assert sender.send_chart_callback is mock_send_chart
        assert sender.send_alert_callback is mock_send_alert

    @pytest.mark.asyncio
    async def test_send_charts_batch_success(
        self,
        mock_chart_generator: MagicMock,
        mock_send_chart: AsyncMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test sending batch of charts successfully."""
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)
        chart_paths = {
            "cpu": "/path/to/cpu.png",
            "memory": "/path/to/memory.png",
        }

        result = await sender.send_charts_batch(chart_paths)

        assert result == 2
        assert mock_send_chart.call_count == 2
        assert mock_chart_generator.cleanup_single_chart_file.call_count == 2

    @pytest.mark.asyncio
    async def test_send_charts_batch_with_caption(
        self,
        mock_chart_generator: MagicMock,
        mock_send_chart: AsyncMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test that caption prefix is used."""
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)
        chart_paths = {"cpu": "/path/to/cpu.png"}

        await sender.send_charts_batch(chart_paths, caption_prefix="TEST")

        mock_send_chart.assert_called_once()
        call_args = mock_send_chart.call_args[0]
        assert call_args[0] == "/path/to/cpu.png"
        assert "TEST" in call_args[1]
        assert "Cpu" in call_args[1]

    @pytest.mark.asyncio
    async def test_send_charts_batch_empty_caption(
        self,
        mock_chart_generator: MagicMock,
        mock_send_chart: AsyncMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test that empty caption prefix results in empty caption."""
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)
        chart_paths = {"cpu": "/path/to/cpu.png"}

        await sender.send_charts_batch(chart_paths, caption_prefix="")

        call_args = mock_send_chart.call_args[0]
        assert call_args[1] == ""

    @pytest.mark.asyncio
    async def test_send_charts_batch_partial_failure(
        self,
        mock_chart_generator: MagicMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test handling partial send failures."""
        mock_send_chart = AsyncMock(side_effect=[True, False])
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)
        chart_paths = {
            "cpu": "/path/to/cpu.png",
            "memory": "/path/to/memory.png",
        }

        result = await sender.send_charts_batch(chart_paths)

        assert result == 1
        assert mock_chart_generator.cleanup_single_chart_file.call_count == 2

    @pytest.mark.asyncio
    async def test_send_charts_batch_all_failures(
        self,
        mock_chart_generator: MagicMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test handling all send failures."""
        mock_send_chart = AsyncMock(return_value=False)
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)
        chart_paths = {"cpu": "/path/to/cpu.png"}

        result = await sender.send_charts_batch(chart_paths)

        assert result == 0
        mock_chart_generator.cleanup_single_chart_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_charts_batch_os_error(
        self,
        mock_chart_generator: MagicMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test handling OSError during send."""
        mock_send_chart = AsyncMock(side_effect=OSError("Filesystem error"))
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)
        chart_paths = {"cpu": "/path/to/cpu.png"}

        result = await sender.send_charts_batch(chart_paths)

        assert result == 0
        mock_chart_generator.cleanup_single_chart_file.assert_called_once()
        mock_send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_charts_batch_empty(
        self,
        mock_chart_generator: MagicMock,
        mock_send_chart: AsyncMock,
        mock_send_alert: AsyncMock,
    ) -> None:
        """Test sending empty batch."""
        sender = ChartBatchSender(mock_chart_generator, mock_send_chart, mock_send_alert)

        result = await sender.send_charts_batch({})

        assert result == 0
        mock_send_chart.assert_not_called()
