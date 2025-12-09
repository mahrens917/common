from unittest.mock import Mock, patch

import pytest

from src.common.websocket.unified_subscription_manager_helpers.factory import (
    UnifiedSubscriptionManagerFactory,
)


class TestUnifiedSubscriptionManagerFactory:
    def test_create_components(self):
        service_name = "test_service"
        websocket_client = Mock()
        subscription_channel = "test_channel"
        active_instruments = {}
        pending_subscriptions = []
        api_type_mapper = Mock()

        with (
            patch(
                "src.common.websocket.unified_subscription_manager_helpers.factory.LifecycleManager"
            ) as MockLifecycle,
            patch(
                "src.common.websocket.unified_subscription_manager_helpers.factory.UpdateHandler"
            ) as MockUpdate,
            patch(
                "src.common.websocket.unified_subscription_manager_helpers.factory.SubscriptionProcessor"
            ) as MockSubProc,
            patch(
                "src.common.websocket.unified_subscription_manager_helpers.factory.HealthValidator"
            ) as MockHealth,
            patch(
                "src.common.websocket.unified_subscription_manager_helpers.factory.MonitoringLoop"
            ) as MockLoop,
        ):

            lifecycle, loop = UnifiedSubscriptionManagerFactory.create_components(
                service_name,
                websocket_client,
                subscription_channel,
                active_instruments,
                pending_subscriptions,
                api_type_mapper,
            )

            assert lifecycle == MockLifecycle.return_value
            assert loop == MockLoop.return_value

            MockLifecycle.assert_called_once_with(service_name)
            MockUpdate.assert_called_once_with(
                service_name,
                websocket_client,
                active_instruments,
                pending_subscriptions,
                api_type_mapper,
            )
            MockSubProc.assert_called_once_with(
                service_name, websocket_client, active_instruments, pending_subscriptions
            )
            MockHealth.assert_called_once_with(service_name, websocket_client, active_instruments)
            MockLoop.assert_called_once_with(
                service_name,
                subscription_channel,
                MockUpdate.return_value,
                MockSubProc.return_value,
                MockHealth.return_value,
            )
