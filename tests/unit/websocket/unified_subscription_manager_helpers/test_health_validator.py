import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.websocket.unified_subscription_manager_helpers.health_validator import (
    HealthValidator,
    SubscriptionHealthError,
)


class TestHealthValidator:
    @pytest.fixture
    def validator(self):
        websocket_client = Mock()
        websocket_client.active_subscriptions = {}
        return HealthValidator("test_service", websocket_client, {})

    @pytest.mark.asyncio
    async def test_validate_health_skip_recent(self, validator):
        validator._last_health_check = time.time()
        await validator.validate_health()
        # Should return without error

    @pytest.mark.asyncio
    async def test_validate_health_zombie_state(self, validator):
        validator._last_health_check = time.time() - 40
        validator.active_instruments = {}
        validator.websocket_client.active_subscriptions = {}

        with patch(
            "src.common.websocket.unified_subscription_manager_helpers.health_validator.Alerter"
        ) as MockAlerter:
            mock_alerter = MockAlerter.return_value
            mock_alerter.send_alert = AsyncMock()

            with pytest.raises(SubscriptionHealthError, match="No active subscriptions"):
                await validator.validate_health()

            mock_alerter.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_health_healthy(self, validator):
        validator._last_health_check = time.time() - 40
        validator.active_instruments = {"inst1": {}}

        await validator.validate_health()
        # Should update last check time
        assert time.time() - validator._last_health_check < 1

    @pytest.mark.asyncio
    async def test_send_health_alert_failure(self, validator):
        with patch(
            "src.common.websocket.unified_subscription_manager_helpers.health_validator.Alerter"
        ) as MockAlerter:
            mock_alerter = MockAlerter.return_value
            mock_alerter.send_alert = AsyncMock(side_effect=ConnectionError("Alert fail"))

            # Should log error but not raise
            await validator._send_health_alert("Test error")
