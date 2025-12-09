import time
from unittest.mock import Mock, patch

import pytest

from src.common.websocket.connection_health_monitor_helpers.health_checker import HealthChecker


class TestHealthChecker:
    @pytest.fixture
    def websocket_client(self):
        client = Mock()
        client.is_connected = True
        client.active_subscriptions = {"sub1": "data"}
        return client

    @pytest.fixture
    def subscription_manager(self):
        manager = Mock()
        manager.active_instruments = {"inst1": "data"}
        return manager

    @pytest.fixture
    def stats_collector(self):
        collector = Mock()
        collector.current_rate = 10
        collector._last_nonzero_update_time = time.time()
        return collector

    @pytest.fixture
    def health_checker(self, websocket_client, subscription_manager, stats_collector):
        return HealthChecker(
            service_name="test_service",
            websocket_client=websocket_client,
            subscription_manager=subscription_manager,
            stats_collector=stats_collector,
            max_silent_duration_seconds=30,
        )

    def test_check_connection_status_success(self, health_checker):
        health_checker.websocket_client.is_connected = True
        health_checker.check_connection_status()

    def test_check_connection_status_failure(self, health_checker):
        health_checker.websocket_client.is_connected = False
        with pytest.raises(ConnectionError, match="test_service WebSocket not connected"):
            health_checker.check_connection_status()

    def test_check_subscription_status_success(self, health_checker):
        health_checker.subscription_manager.active_instruments = {"inst1": "data"}
        health_checker.websocket_client.active_subscriptions = {"sub1": "data"}
        health_checker.check_subscription_status()

    def test_check_subscription_status_failure(self, health_checker):
        health_checker.subscription_manager.active_instruments = {}
        health_checker.websocket_client.active_subscriptions = {}
        with pytest.raises(
            ConnectionError, match="test_service has no active subscriptions - zombie state"
        ):
            health_checker.check_subscription_status()

    def test_check_data_flow_success(self, health_checker):
        current_time = time.time()
        health_checker.stats_collector._last_nonzero_update_time = current_time - 10

        time_diff = health_checker.check_data_flow(current_time)
        assert time_diff == 10.0

    def test_check_data_flow_failure(self, health_checker):
        current_time = time.time()
        health_checker.stats_collector._last_nonzero_update_time = current_time - 40

        with pytest.raises(ConnectionError, match="test_service no data flow for"):
            health_checker.check_data_flow(current_time)

    def test_log_health_check_passed(self, health_checker):
        with patch(
            "src.common.websocket.connection_health_monitor_helpers.health_checker.logger"
        ) as mock_logger:
            health_checker.log_health_check_passed(5.0)
            mock_logger.debug.assert_called_once()
            assert "test_service health check passed" in mock_logger.debug.call_args[0][0]

    def test_is_healthy_sync_success(self, health_checker):
        assert health_checker.is_healthy_sync() is True

    def test_is_healthy_sync_disconnected(self, health_checker):
        health_checker.websocket_client.is_connected = False
        assert health_checker.is_healthy_sync() is False

    def test_is_healthy_sync_no_subscriptions(self, health_checker):
        health_checker.subscription_manager.active_instruments = {}
        # websocket active subscriptions doesn't matter for is_healthy_sync logic if implemented as written in source,
        # actually the source checks subscription_manager.active_instruments length.
        # Let's verify the source code logic:
        # if len(self.subscription_manager.active_instruments) == 0: return False
        assert health_checker.is_healthy_sync() is False

    def test_is_healthy_sync_stale_data(self, health_checker):
        health_checker.stats_collector._last_nonzero_update_time = time.time() - 40
        assert health_checker.is_healthy_sync() is False

    def test_is_healthy_sync_exception(self, health_checker):
        from unittest.mock import PropertyMock

        # Re-setup mock since PropertyMock needs to be applied to the object or class
        health_checker.websocket_client = Mock()
        p = PropertyMock(side_effect=RuntimeError("Error"))
        type(health_checker.websocket_client).is_connected = p

        assert health_checker.is_healthy_sync() is False
