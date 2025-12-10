"""Tests for common websocket interfaces module."""

from __future__ import annotations

from typing import List, Set

from common.websocket.interfaces import SubscriptionAwareWebSocketClient


class TestSubscriptionAwareWebSocketClient:
    """Tests for SubscriptionAwareWebSocketClient protocol."""

    def test_protocol_is_importable(self) -> None:
        """Protocol can be imported from module."""
        from common.websocket import interfaces

        assert "SubscriptionAwareWebSocketClient" in interfaces.__all__

    def test_protocol_can_be_used_as_type(self) -> None:
        """Protocol can be used as a type hint."""
        # This verifies the protocol is properly defined

        class MockClient:
            """Mock implementation of SubscriptionAwareWebSocketClient."""

            @property
            def is_connected(self) -> bool:
                return True

            @property
            def active_subscriptions(self) -> Set[str]:
                return {"channel1", "channel2"}

            async def subscribe(self, channels: List[str]) -> bool:
                return True

            async def unsubscribe(self, channels: List[str]) -> bool:
                return True

        # Verify mock client satisfies the protocol
        client: SubscriptionAwareWebSocketClient = MockClient()
        assert client.is_connected is True
        assert "channel1" in client.active_subscriptions

    def test_protocol_checks_is_connected_property(self) -> None:
        """Protocol requires is_connected property."""

        class MockConnectedClient:
            @property
            def is_connected(self) -> bool:
                return False

            @property
            def active_subscriptions(self) -> Set[str]:
                return set()

            async def subscribe(self, channels: List[str]) -> bool:
                return True

            async def unsubscribe(self, channels: List[str]) -> bool:
                return True

        client = MockConnectedClient()
        assert client.is_connected is False

    def test_protocol_checks_active_subscriptions_property(self) -> None:
        """Protocol requires active_subscriptions property."""

        class MockSubscriptionsClient:
            @property
            def is_connected(self) -> bool:
                return True

            @property
            def active_subscriptions(self) -> Set[str]:
                return {"test_channel"}

            async def subscribe(self, channels: List[str]) -> bool:
                return True

            async def unsubscribe(self, channels: List[str]) -> bool:
                return True

        client = MockSubscriptionsClient()
        assert "test_channel" in client.active_subscriptions

    async def test_protocol_defines_subscribe_method(self) -> None:
        """Protocol defines subscribe async method."""

        class MockSubscribeClient:
            @property
            def is_connected(self) -> bool:
                return True

            @property
            def active_subscriptions(self) -> Set[str]:
                return set()

            async def subscribe(self, channels: List[str]) -> bool:
                return len(channels) > 0

            async def unsubscribe(self, channels: List[str]) -> bool:
                return True

        client = MockSubscribeClient()
        result = await client.subscribe(["channel1"])
        assert result is True

    async def test_protocol_defines_unsubscribe_method(self) -> None:
        """Protocol defines unsubscribe async method."""

        class MockUnsubscribeClient:
            @property
            def is_connected(self) -> bool:
                return True

            @property
            def active_subscriptions(self) -> Set[str]:
                return {"channel1"}

            async def subscribe(self, channels: List[str]) -> bool:
                return True

            async def unsubscribe(self, channels: List[str]) -> bool:
                return len(channels) > 0

        client = MockUnsubscribeClient()
        result = await client.unsubscribe(["channel1"])
        assert result is True
