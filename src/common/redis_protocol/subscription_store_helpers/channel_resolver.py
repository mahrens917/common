"""
Channel and hash key resolution for subscription services.
"""

from .. import config


class ChannelResolver:
    """Resolves service-specific subscription channels and hash keys"""

    def __init__(self, service_type: str):
        """Initialize with service type

        Args:
            service_type: Service type ('deribit' or 'kalshi')

        Raises:
            ValueError: If service_type is invalid
        """
        if service_type not in ["deribit", "kalshi"]:
            raise TypeError(f"Invalid service_type: {service_type}. Must be 'deribit' or 'kalshi'")
        self.service_type = service_type

    def get_subscription_channel(self) -> str:
        """Get the appropriate subscription channel for this service type"""
        if self.service_type == "kalshi":
            return config.KALSHI_SUBSCRIPTION_CHANNEL
        return config.DERIBIT_SUBSCRIPTION_CHANNEL

    def get_subscription_hash(self) -> str:
        """Get the hash key used to store subscriptions for this service"""
        if self.service_type == "kalshi":
            return config.KALSHI_SUBSCRIPTION_KEY
        return config.DERIBIT_SUBSCRIPTION_KEY
