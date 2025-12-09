from __future__ import annotations

"""Shared typing interfaces for WebSocket helpers."""


from typing import List, Protocol, Set


class SubscriptionAwareWebSocketClient(Protocol):
    """Protocol capturing the shared WebSocket client surface."""

    @property
    def is_connected(self) -> bool:
        """Return True when the client currently has an open connection."""
        ...

    @property
    def active_subscriptions(self) -> Set[str]:
        """Return the set of active subscription identifiers."""
        ...

    async def subscribe(self, channels: List[str]) -> bool:
        """Subscribe to WebSocket channels."""
        ...

    async def unsubscribe(self, channels: List[str]) -> bool:
        """Unsubscribe from WebSocket channels."""
        ...


__all__ = ["SubscriptionAwareWebSocketClient"]
