"""Tests for command_queue_processor module."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.alerter_helpers.command_queue_processor import CommandQueueProcessor
from common.alerting import AlertSeverity, QueuedCommand


@pytest.fixture
def mock_queue() -> asyncio.Queue:
    """Create a mock command queue."""
    return asyncio.Queue()


@pytest.fixture
def mock_send_alert() -> AsyncMock:
    """Create a mock send alert callback."""
    return AsyncMock()


class TestCommandQueueProcessor:
    """Tests for CommandQueueProcessor class."""

    def test_init(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test CommandQueueProcessor initialization."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)

        assert processor.command_queue is mock_queue
        assert processor.send_alert_callback is mock_send_alert
        assert processor.is_processing is False
        assert processor.processor_task is None

    @pytest.mark.asyncio
    async def test_start_creates_task(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test start creates processor task."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)

        await processor.start()

        assert processor.processor_task is not None
        assert not processor.processor_task.done()

        await processor.stop()

    @pytest.mark.asyncio
    async def test_start_does_not_create_duplicate_task(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test start does not create duplicate task if already running."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)

        await processor.start()
        first_task = processor.processor_task

        await processor.start()

        assert processor.processor_task is first_task

        await processor.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test stop cancels the processor task."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)

        await processor.start()
        assert processor.processor_task is not None

        await processor.stop()

        assert processor.processor_task.done()

    @pytest.mark.asyncio
    async def test_stop_with_no_task(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test stop with no running task."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_command_success(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test processing command successfully."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)
        handler = AsyncMock()
        message = MagicMock()
        command = QueuedCommand(command="test", handler=handler, message=message, timestamp=time.time())

        await processor.start()
        await mock_queue.put(command)
        await asyncio.sleep(0.1)

        handler.assert_called_once_with(message)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_command_error_sends_alert(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test processing command error sends alert."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)
        handler = AsyncMock(side_effect=ValueError("Test error"))
        message = MagicMock()
        command = QueuedCommand(command="test", handler=handler, message=message, timestamp=time.time())

        await processor.start()
        await mock_queue.put(command)
        await asyncio.sleep(0.1)

        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args
        assert "Error executing command" in call_args[0][0]
        assert call_args[0][1] == AlertSeverity.WARNING

        await processor.stop()

    @pytest.mark.asyncio
    async def test_process_multiple_commands(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test processing multiple commands."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        message1 = MagicMock()
        message2 = MagicMock()

        await processor.start()
        await mock_queue.put(QueuedCommand(command="cmd1", handler=handler1, message=message1, timestamp=time.time()))
        await mock_queue.put(QueuedCommand(command="cmd2", handler=handler2, message=message2, timestamp=time.time()))
        await asyncio.sleep(0.2)

        handler1.assert_called_once_with(message1)
        handler2.assert_called_once_with(message2)

        await processor.stop()

    @pytest.mark.asyncio
    async def test_is_processing_flag(self, mock_queue: asyncio.Queue, mock_send_alert: AsyncMock) -> None:
        """Test is_processing flag is set during processing."""
        processor = CommandQueueProcessor(mock_queue, mock_send_alert)

        assert processor.is_processing is False

        await processor.start()
        await asyncio.sleep(0.05)

        assert processor.is_processing is True

        await processor.stop()
        await asyncio.sleep(0.05)

        assert processor.is_processing is False
