import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.connection_health_monitor import ConnectionHealthMonitor


class TestConnectionHealthMonitor:
    @pytest.fixture
    def monitor(self):
        websocket_client = Mock()
        subscription_manager = Mock()
        stats_collector = Mock()
        return ConnectionHealthMonitor(
            service_name="test_service",
            websocket_client=websocket_client,
            subscription_manager=subscription_manager,
            stats_collector=stats_collector,
            health_check_interval_seconds=30,
            max_silent_duration_seconds=300,
        )

    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor):
        monitor._lifecycle = Mock()
        monitor._lifecycle.start_monitoring = AsyncMock()

        await monitor.start_monitoring()
        monitor._lifecycle.start_monitoring.assert_called_once_with(monitor.check_health)

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor):
        monitor._lifecycle = Mock()
        monitor._lifecycle.stop_monitoring = AsyncMock()

        await monitor.stop_monitoring()
        monitor._lifecycle.stop_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_skipped_too_soon(self, monitor):
        monitor._last_health_check = time.time()
        monitor._health_checker = Mock()

        with patch(
            "common.websocket.connection_health_monitor.time.time",
            return_value=monitor._last_health_check + 10,
        ):
            await monitor.check_health()
            monitor._health_checker.check_connection_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_success(self, monitor):
        import time

        monitor._last_health_check = time.time() - 40
        monitor._health_checker = Mock()
        monitor._health_checker.check_data_flow.return_value = 5.0
        monitor._alert_sender = Mock()

        await monitor.check_health()

        monitor._health_checker.check_connection_status.assert_called_once()
        monitor._health_checker.check_subscription_status.assert_called_once()
        monitor._health_checker.check_data_flow.assert_called_once()
        monitor._health_checker.log_health_check_passed.assert_called_once_with(5.0)

    @pytest.mark.asyncio
    async def test_check_health_connection_error(self, monitor):
        import time

        monitor._last_health_check = time.time() - 40
        monitor._health_checker = Mock()
        monitor._health_checker.check_connection_status.side_effect = ConnectionError("Fail")
        monitor._alert_sender = Mock()
        monitor._alert_sender.send_health_alert = AsyncMock()

        with pytest.raises(ConnectionError):
            await monitor.check_health()

        monitor._alert_sender.send_health_alert.assert_called_once_with("Fail", "connection_down")

    @pytest.mark.asyncio
    async def test_check_health_subscription_error(self, monitor):
        import time

        monitor._last_health_check = time.time() - 40
        monitor._health_checker = Mock()
        monitor._health_checker.check_subscription_status.side_effect = ConnectionError("Fail")
        monitor._alert_sender = Mock()
        monitor._alert_sender.send_health_alert = AsyncMock()

        with pytest.raises(ConnectionError):
            await monitor.check_health()

        monitor._alert_sender.send_health_alert.assert_called_once_with("Fail", "no_subscriptions")

    @pytest.mark.asyncio
    async def test_check_health_data_flow_error(self, monitor):
        import time

        monitor._last_health_check = time.time() - 40
        monitor._health_checker = Mock()
        monitor._health_checker.check_data_flow.side_effect = ConnectionError("Fail")
        monitor._alert_sender = Mock()
        monitor._alert_sender.send_health_alert = AsyncMock()

        with pytest.raises(ConnectionError):
            await monitor.check_health()

        monitor._alert_sender.send_health_alert.assert_called_once_with("Fail", "no_data_flow")

    def test_is_healthy(self, monitor):
        monitor._health_checker = Mock()
        monitor._health_checker.is_healthy_sync.return_value = True

        assert monitor.is_healthy() is True
        monitor._health_checker.is_healthy_sync.assert_called_once()
