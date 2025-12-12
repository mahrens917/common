import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.message_stats_helpers import silent_failure_alerter
from src.monitor.alerter import AlertSeverity


class TestSilentFailureAlerter:
    @pytest.mark.asyncio
    async def test_send_silent_failure_alert_success(self):
        with patch("src.monitor.alerter.Alerter") as MockAlerter:
            mock_alerter_instance = MockAlerter.return_value
            mock_alerter_instance.send_alert = AsyncMock()

            await silent_failure_alerter.send_silent_failure_alert("test_service", 30.5)

            mock_alerter_instance.send_alert.assert_called_once_with(
                message="🔴 TEST_SERVICE_WS - Silent failure detected - No messages for 30.5s",
                severity=AlertSeverity.CRITICAL,
                alert_type="test_service_ws_silent_failure",
            )

    @pytest.mark.asyncio
    async def test_send_silent_failure_alert_exception(self):
        with patch("src.monitor.alerter.Alerter") as MockAlerter:
            mock_alerter_instance = MockAlerter.return_value
            mock_alerter_instance.send_alert = AsyncMock(side_effect=ConnectionError("Alert failed"))

            with patch("common.websocket.message_stats_helpers.silent_failure_alerter.logger") as mock_logger:
                await silent_failure_alerter.send_silent_failure_alert("test_service", 30.5)
                mock_logger.exception.assert_called_once()

    def test_check_silent_failure_threshold_rate_positive(self):
        assert (
            silent_failure_alerter.check_silent_failure_threshold(
                current_rate=5,
                current_time=100,
                last_nonzero_update_time=90,
                threshold_seconds=20,
                service_name="test",
            )
            is False
        )

    def test_check_silent_failure_threshold_below_threshold(self):
        assert (
            silent_failure_alerter.check_silent_failure_threshold(
                current_rate=0,
                current_time=100,
                last_nonzero_update_time=90,
                threshold_seconds=20,
                service_name="test",
            )
            is False
        )

    def test_check_silent_failure_threshold_exceeded(self):
        with patch("common.websocket.message_stats_helpers.silent_failure_alerter.logger") as mock_logger:
            assert (
                silent_failure_alerter.check_silent_failure_threshold(
                    current_rate=0,
                    current_time=100,
                    last_nonzero_update_time=50,
                    threshold_seconds=20,
                    service_name="test",
                )
                is True
            )
            mock_logger.error.assert_called_once()
            assert "SILENT_FAILURE_DETECTION" in mock_logger.error.call_args[0][0]
