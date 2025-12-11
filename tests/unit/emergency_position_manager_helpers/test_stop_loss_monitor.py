"""Tests for stop loss monitor module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.emergency_position_manager_helpers.stop_loss_monitor import StopLossMonitor

DEFAULT_STOP_LOSS_MONITOR_CALL_THRESHOLD = 2


class TestStopLossMonitorInit:
    """Tests for StopLossMonitor initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with trading client and position closer."""
        client = MagicMock()
        closer = MagicMock()

        monitor = StopLossMonitor(trading_client=client, position_closer=closer)

        assert monitor.trading_client is client
        assert monitor.position_closer is closer


class TestStopLossMonitorCreateStopLossMonitor:
    """Tests for StopLossMonitor.create_stop_loss_monitor."""

    @pytest.mark.asyncio
    async def test_exits_when_ticker_removed_from_monitored(self) -> None:
        """Exits loop when ticker is removed from monitored positions."""
        client = MagicMock()
        closer = MagicMock()
        monitor = StopLossMonitor(trading_client=client, position_closer=closer)
        monitored_positions = {}

        with patch("common.emergency_position_manager_helpers.stop_loss_monitor.logger"):
            await monitor.create_stop_loss_monitor("KXBTC-25JAN01", -500, monitored_positions, check_interval_seconds=0.01)

    @pytest.mark.asyncio
    async def test_exits_when_position_no_longer_exists(self) -> None:
        """Exits loop when position no longer exists."""
        client = MagicMock()
        client.get_portfolio_positions = AsyncMock(return_value=[])
        closer = MagicMock()
        monitor = StopLossMonitor(trading_client=client, position_closer=closer)
        monitored_positions = {"KXBTC-25JAN01": True}

        with patch("common.emergency_position_manager_helpers.stop_loss_monitor.logger"):
            await monitor.create_stop_loss_monitor("KXBTC-25JAN01", -500, monitored_positions, check_interval_seconds=0.01)

    @pytest.mark.asyncio
    async def test_triggers_close_when_stop_loss_hit(self) -> None:
        """Triggers emergency close when stop loss threshold hit."""
        client = MagicMock()
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.unrealized_pnl_cents = -600
        client.get_portfolio_positions = AsyncMock(return_value=[position])
        closer = MagicMock()
        closer.emergency_close_position = AsyncMock()
        monitor = StopLossMonitor(trading_client=client, position_closer=closer)
        monitored_positions = {"KXBTC-25JAN01": True}

        with patch("common.emergency_position_manager_helpers.stop_loss_monitor.logger"):
            await monitor.create_stop_loss_monitor("KXBTC-25JAN01", -500, monitored_positions, check_interval_seconds=0.01)

        closer.emergency_close_position.assert_called_once_with(position, "Stop-loss triggered")

    @pytest.mark.asyncio
    async def test_handles_trading_error(self) -> None:
        """Handles trading errors gracefully and continues monitoring."""
        from common.trading_exceptions import KalshiTradingError

        client = MagicMock()
        call_count = 0

        async def mock_get_positions():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise KalshiTradingError("API error")
            return []

        client.get_portfolio_positions = mock_get_positions
        closer = MagicMock()
        monitor = StopLossMonitor(trading_client=client, position_closer=closer)
        monitored_positions = {"KXBTC-25JAN01": True}

        with patch("common.emergency_position_manager_helpers.stop_loss_monitor.logger"):
            await monitor.create_stop_loss_monitor("KXBTC-25JAN01", -500, monitored_positions, check_interval_seconds=0.01)

        assert call_count >= DEFAULT_STOP_LOSS_MONITOR_CALL_THRESHOLD

    @pytest.mark.asyncio
    async def test_continues_when_above_threshold(self) -> None:
        """Continues monitoring when P&L is above threshold."""
        client = MagicMock()
        call_count = 0

        async def mock_get_positions():
            nonlocal call_count
            call_count += 1
            if call_count >= DEFAULT_STOP_LOSS_MONITOR_CALL_THRESHOLD:
                return []
            position = MagicMock()
            position.ticker = "KXBTC-25JAN01"
            position.unrealized_pnl_cents = -100
            return [position]

        client.get_portfolio_positions = mock_get_positions
        closer = MagicMock()
        monitor = StopLossMonitor(trading_client=client, position_closer=closer)
        monitored_positions = {"KXBTC-25JAN01": True}

        with patch("common.emergency_position_manager_helpers.stop_loss_monitor.logger"):
            await monitor.create_stop_loss_monitor("KXBTC-25JAN01", -500, monitored_positions, check_interval_seconds=0.01)

        closer.emergency_close_position.assert_not_called()
