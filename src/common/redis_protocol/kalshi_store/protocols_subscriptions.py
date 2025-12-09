from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Sequence, Set


class ISubscriptionTracker(Protocol):
    """Protocol for subscription tracking operations."""

    SUBSCRIPTIONS_KEY: str
    SERVICE_STATUS_KEY: str
    SUBSCRIBED_MARKETS_KEY: str
    SUBSCRIPTION_IDS_KEY: str

    async def get_subscribed_markets(self) -> Set[str]:
        """Get all subscribed markets for current service."""
        ...

    async def add_subscribed_market(
        self,
        market_ticker: str,
        *,
        category: Optional[str] = None,
    ) -> bool:
        """Add market to subscribed markets."""
        ...

    async def remove_subscribed_market(
        self,
        market_ticker: str,
        *,
        category: Optional[str] = None,
    ) -> bool:
        """Remove market from subscribed markets."""
        ...

    async def record_subscription_ids(
        self,
        subscription_ids: Dict[str, Any] | Sequence[Any],
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        """Record subscription IDs for markets."""
        ...

    async def fetch_subscription_ids(
        self,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> Dict[str, str]:
        """Fetch subscription IDs for markets."""
        ...

    async def clear_subscription_ids(
        self,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        """Clear subscription IDs for markets."""
        ...

    async def update_service_status(self, service: str, status: Dict[str, Any]) -> bool:
        """Update service status."""
        ...

    async def get_service_status(self, service: str) -> Optional[str]:
        """Get service status."""
        ...


class ISubscriptionDelegator(Protocol):
    """Protocol for subscription delegation operations."""

    SUBSCRIPTIONS_KEY: str
    SERVICE_STATUS_KEY: str
    SUBSCRIBED_MARKETS_KEY: str
    SUBSCRIPTION_IDS_KEY: str

    async def get_subscribed_markets(self) -> Set[str]:
        """Get subscribed markets."""
        ...

    async def add_subscribed_market(
        self,
        market_ticker: str,
        *,
        category: Optional[str] = None,
    ) -> bool:
        """Add subscribed market."""
        ...

    async def remove_subscribed_market(
        self,
        market_ticker: str,
        *,
        category: Optional[str] = None,
    ) -> bool:
        """Remove subscribed market."""
        ...

    async def record_subscription_ids(
        self,
        subscription_ids: Dict[str, Any] | Sequence[Any],
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        """Record subscription IDs."""
        ...

    async def fetch_subscription_ids(
        self,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> Dict[str, str]:
        """Fetch subscription IDs."""
        ...

    async def clear_subscription_ids(
        self,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        """Clear subscription IDs."""
        ...

    async def update_service_status(self, service: str, status: Dict[str, Any]) -> bool:
        """Update service status."""
        ...

    async def get_service_status(self, service: str) -> Optional[str]:
        """Get service status."""
        ...
