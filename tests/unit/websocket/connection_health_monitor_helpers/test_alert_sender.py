from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.connection_health_monitor_helpers.alert_sender import (
    ALERT_FAILURE_ERRORS,
    HealthAlertSender,
)
from src.monitor.alerter import AlertSeverity


class TestHealthAlertSender:
    @pytest.fixture
    def sender(self):
        return HealthAlertSender("test_service")

    @pytest.mark.asyncio
    async def test_send_health_alert_success(self, sender):
        with patch(
            "common.websocket.connection_health_monitor_helpers.alert_sender.Alerter"
        ) as MockAlerter:
            mock_alerter_instance = MockAlerter.return_value
            mock_alerter_instance.send_alert = AsyncMock()

            await sender.send_health_alert("Test failure", "test_alert")

            mock_alerter_instance.send_alert.assert_called_once_with(
                message="🔴 TEST_SERVICE_WS - Health check failed: Test failure",
                severity=AlertSeverity.CRITICAL,
                alert_type="test_service_ws_test_alert",
            )

    @pytest.mark.asyncio
    async def test_send_health_alert_failure(self, sender):
        with patch(
            "common.websocket.connection_health_monitor_helpers.alert_sender.Alerter"
        ) as MockAlerter:
            mock_alerter_instance = MockAlerter.return_value
            mock_alerter_instance.send_alert = AsyncMock(
                side_effect=ConnectionError("Alert failed")
            )

            # Should catch exception and log it, not raise
            await sender.send_health_alert("Test failure", "test_alert")

            mock_alerter_instance.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_health_alert_failure_timeout(self, sender):
        with patch(
            "common.websocket.connection_health_monitor_helpers.alert_sender.Alerter"
        ) as MockAlerter:
            mock_alerter_instance = MockAlerter.return_value
            mock_alerter_instance.send_alert = AsyncMock(side_effect=TimeoutError("Timeout"))

            # Should catch exception and log it, not raise
            await sender.send_health_alert("Test failure", "test_alert")

            mock_alerter_instance.send_alert.assert_called_once()
