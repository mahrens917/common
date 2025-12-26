"""Tests for lifecycle_helpers module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alerter_helpers.lifecycle_helpers import LifecycleHelpers


@pytest.fixture
def mock_component_manager() -> MagicMock:
    """Create a mock component manager."""
    manager = MagicMock()
    manager.telegram_enabled = True
    manager.cmd_processor = MagicMock()
    manager.get_telegram_component = MagicMock(return_value=MagicMock())
    return manager


class TestLifecycleHelpers:
    """Tests for LifecycleHelpers class."""

    def test_init(self, mock_component_manager: MagicMock) -> None:
        """Test LifecycleHelpers initialization."""
        helpers = LifecycleHelpers(mock_component_manager)
        assert helpers._mgr is mock_component_manager

    def test_ensure_proc_with_telegram_enabled(self, mock_component_manager: MagicMock) -> None:
        """Test ensure_proc calls ensure_processor when Telegram is enabled."""
        helpers = LifecycleHelpers(mock_component_manager)

        with patch.object(helpers, "ensure_processor") as mock_ensure:
            helpers.ensure_proc()
            mock_ensure.assert_called_once_with(mock_component_manager.cmd_processor)

    def test_ensure_proc_with_telegram_disabled(self, mock_component_manager: MagicMock) -> None:
        """Test ensure_proc does nothing when Telegram is disabled."""
        mock_component_manager.telegram_enabled = False
        helpers = LifecycleHelpers(mock_component_manager)

        with patch.object(helpers, "ensure_processor") as mock_ensure:
            helpers.ensure_proc()
            mock_ensure.assert_not_called()

    @pytest.mark.asyncio
    async def test_flush(self, mock_component_manager: MagicMock) -> None:
        """Test flush method completes without error."""
        helpers = LifecycleHelpers(mock_component_manager)
        await helpers.flush()

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_component_manager: MagicMock) -> None:
        """Test cleanup calls cleanup_resources."""
        cmd_processor = AsyncMock()
        mock_component_manager.get_telegram_component.return_value = cmd_processor
        helpers = LifecycleHelpers(mock_component_manager)

        with patch.object(LifecycleHelpers, "cleanup_resources", new_callable=AsyncMock) as mock_cleanup:
            await helpers.cleanup()
            mock_cleanup.assert_called_once_with(True, cmd_processor)

    def test_ensure_processor_with_running_loop(self) -> None:
        """Test ensure_processor creates task when loop is running."""

        async def run_test():
            command_processor = MagicMock()
            command_processor.start = AsyncMock()

            with patch("common.alerter_helpers.lifecycle_helpers.asyncio") as mock_asyncio:
                mock_asyncio.get_running_loop.return_value = MagicMock()
                LifecycleHelpers.ensure_processor(command_processor)
                mock_asyncio.create_task.assert_called_once()

        asyncio.run(run_test())

    def test_ensure_processor_without_running_loop(self) -> None:
        """Test ensure_processor handles no running loop gracefully."""
        command_processor = MagicMock()

        with patch(
            "common.alerter_helpers.lifecycle_helpers.asyncio.get_running_loop",
            side_effect=RuntimeError("No running loop"),
        ):
            LifecycleHelpers.ensure_processor(command_processor)

    @pytest.mark.asyncio
    async def test_cleanup_resources_with_telegram_enabled(self) -> None:
        """Test cleanup_resources stops command processor when Telegram is enabled."""
        command_processor = AsyncMock()
        command_processor.stop = AsyncMock()

        await LifecycleHelpers.cleanup_resources(telegram_enabled=True, command_processor=command_processor)

        command_processor.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_resources_with_telegram_disabled(self) -> None:
        """Test cleanup_resources does nothing when Telegram is disabled."""
        command_processor = AsyncMock()
        command_processor.stop = AsyncMock()

        await LifecycleHelpers.cleanup_resources(telegram_enabled=False, command_processor=command_processor)

        command_processor.stop.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_resources_with_none_processor(self) -> None:
        """Test cleanup_resources handles None processor gracefully."""
        await LifecycleHelpers.cleanup_resources(telegram_enabled=True, command_processor=None)
