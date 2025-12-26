"""Tests for alerter_helpers.command_coordinator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alerter_helpers.command_coordinator import CommandCoordinator


class TestCommandCoordinatorInit:
    """Tests for CommandCoordinator initialization."""

    def test_stores_dependencies(self) -> None:
        """Test initialization stores dependencies."""
        mock_chart_mgr = MagicMock()
        mock_send_alert = MagicMock()
        mock_send_chart = MagicMock()

        coordinator = CommandCoordinator(mock_chart_mgr, mock_send_alert, mock_send_chart)

        assert coordinator.chart_mgr == mock_chart_mgr
        assert coordinator.send_alert == mock_send_alert
        assert coordinator.send_chart == mock_send_chart


class TestCommandCoordinatorHandleHelp:
    """Tests for handle_help method."""

    @pytest.mark.asyncio
    async def test_handles_help_command(self) -> None:
        """Test handles help command."""
        mock_chart_mgr = MagicMock()
        mock_send_alert = AsyncMock()
        mock_send_chart = MagicMock()

        coordinator = CommandCoordinator(mock_chart_mgr, mock_send_alert, mock_send_chart)

        with patch("common.alerter_helpers.command_handlers.HelpCommandHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock()
            mock_handler_class.return_value = mock_handler

            await coordinator.handle_help({})

            mock_handler_class.assert_called_once()
            mock_handler.handle.assert_called_once_with(mock_send_alert)


class TestCommandCoordinatorHandleLoad:
    """Tests for handle_load method."""

    @pytest.mark.asyncio
    async def test_handles_load_command(self) -> None:
        """Test handles load command."""
        mock_chart_mgr = MagicMock()
        mock_chart_mgr.chart_generator = MagicMock()
        mock_send_alert = AsyncMock()
        mock_send_chart = AsyncMock()

        coordinator = CommandCoordinator(mock_chart_mgr, mock_send_alert, mock_send_chart)
        message = {"chat": {"id": "123"}}

        with patch("common.alerter_helpers.command_handlers.LoadCommandHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock()
            mock_handler_class.return_value = mock_handler

            await coordinator.handle_load(message)

            mock_chart_mgr.ensure_chart_dependencies_initialized.assert_called_once()
            mock_handler.handle.assert_called_once_with(message)


class TestCommandCoordinatorHandlePnl:
    """Tests for handle_pnl method."""

    @pytest.mark.asyncio
    async def test_handles_pnl_command(self) -> None:
        """Test handles pnl command."""
        mock_chart_mgr = MagicMock()
        mock_chart_mgr.pnl_reporter = MagicMock()
        mock_chart_mgr.chart_generator = MagicMock()
        mock_chart_mgr.ensure_pnl_reporter = AsyncMock()
        mock_send_alert = AsyncMock()
        mock_send_chart = AsyncMock()

        coordinator = CommandCoordinator(mock_chart_mgr, mock_send_alert, mock_send_chart)
        message = {"chat": {"id": "123"}}

        with patch("common.alerter_helpers.command_handlers.PnlCommandHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock()
            mock_handler_class.return_value = mock_handler

            await coordinator.handle_pnl(message)

            mock_chart_mgr.ensure_chart_dependencies_initialized.assert_called_once()
            mock_handler.handle.assert_called_once_with(message)


class TestCommandCoordinatorHandlePrice:
    """Tests for handle_price method."""

    @pytest.mark.asyncio
    async def test_handles_price_command(self) -> None:
        """Test handles price command."""
        mock_chart_mgr = MagicMock()
        mock_send_alert = AsyncMock()
        mock_send_chart = AsyncMock()

        coordinator = CommandCoordinator(mock_chart_mgr, mock_send_alert, mock_send_chart)
        message = {"chat": {"id": "123"}}

        with patch("common.alerter_helpers.command_handlers.PriceCommandHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock()
            mock_handler_class.return_value = mock_handler

            await coordinator.handle_price(message)

            mock_chart_mgr.ensure_chart_dependencies_initialized.assert_called_once()
            mock_handler.handle.assert_called_once_with(message)


class TestCommandCoordinatorHandleTemp:
    """Tests for handle_temp method."""

    @pytest.mark.asyncio
    async def test_handles_temp_command(self) -> None:
        """Test handles temp command."""
        mock_chart_mgr = MagicMock()
        mock_chart_mgr.chart_generator = MagicMock()
        mock_send_alert = AsyncMock()
        mock_send_chart = AsyncMock()

        coordinator = CommandCoordinator(mock_chart_mgr, mock_send_alert, mock_send_chart)
        message = {"chat": {"id": "123"}}

        with patch("common.alerter_helpers.command_handlers.TempCommandHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock()
            mock_handler_class.return_value = mock_handler

            await coordinator.handle_temp(message)

            mock_chart_mgr.ensure_chart_dependencies_initialized.assert_called_once()
            mock_handler.handle.assert_called_once_with(message)
