"""
Redis key provider for KalshiSubscriptionTracker
"""


class KeyProvider:
    """Provides Redis key names for subscription tracking"""

    def __init__(self, service_prefix: str):
        """
        Initialize key provider

        Args:
            service_prefix: 'rest' or 'ws'
        """
        self._service_prefix = service_prefix

    @property
    def subscriptions_key(self) -> str:
        """Get subscriptions key"""
        return "kalshi:subscriptions"

    @property
    def service_status_key(self) -> str:
        """Get service status key"""
        return "status"

    @property
    def subscribed_markets_key(self) -> str:
        """Get subscribed markets key"""
        return "kalshi:subscribed_markets"

    @property
    def subscription_ids_key(self) -> str:
        """Get subscription IDs key"""
        return f"kalshi:subscription_ids:{self._service_prefix}"
