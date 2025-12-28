"""Tests for lifecycle module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.kalshi_trading_client.client_helpers.lifecycle import LifecycleManager


class TestLifecycleManager:
    """Tests for LifecycleManager class."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        mock_client = MagicMock()
        mock_client.initialize = AsyncMock()

        await LifecycleManager.initialize(mock_client)

        mock_client.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_success(self):
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_trade_store_manager = MagicMock()
        mock_trade_store_manager.close_managed = AsyncMock()

        await LifecycleManager.close(mock_client, mock_trade_store_manager)

        mock_client.close.assert_called_once()
        mock_trade_store_manager.close_managed.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_handles_client_error(self):
        mock_client = MagicMock()
        mock_client.close = AsyncMock(side_effect=RuntimeError("Close failed"))
        mock_trade_store_manager = MagicMock()
        mock_trade_store_manager.close_managed = AsyncMock()

        await LifecycleManager.close(mock_client, mock_trade_store_manager)

        mock_trade_store_manager.close_managed.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_handles_connection_error(self):
        mock_client = MagicMock()
        mock_client.close = AsyncMock(side_effect=ConnectionError("Connection lost"))
        mock_trade_store_manager = MagicMock()
        mock_trade_store_manager.close_managed = AsyncMock()

        await LifecycleManager.close(mock_client, mock_trade_store_manager)

        mock_trade_store_manager.close_managed.assert_called_once()

    def test_log_context_exit_no_exception(self):
        result = LifecycleManager.log_context_exit(None, None, None)

        assert result is False

    def test_log_context_exit_with_exception(self):
        result = LifecycleManager.log_context_exit(
            ValueError,
            ValueError("Test error"),
            None,
        )

        assert result is False

    def test_log_context_exit_with_runtime_error(self):
        result = LifecycleManager.log_context_exit(
            RuntimeError,
            RuntimeError("Runtime failure"),
            None,
        )

        assert result is False
