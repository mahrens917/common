"""Delay calculation helpers for backoff management."""

import logging

from common.backoff_manager import random as backoff_random

from .types import BackoffConfig

logger = logging.getLogger(__name__)


class DelayCalculator:
    """Calculates backoff delays with jitter and network awareness."""

    @staticmethod
    def calculate_base_delay(config: BackoffConfig, attempt: int) -> float:
        """
        Calculate base exponential backoff delay.

        Args:
            config: Backoff configuration
            attempt: Attempt number

        Returns:
            Base delay in seconds
        """
        return min(config.initial_delay * (config.multiplier ** (attempt - 1)), config.max_delay)

    @staticmethod
    def apply_network_multiplier(
        base_delay: float,
        config: BackoffConfig,
        network_health_monitor,
        service_name: str,
    ) -> float:
        """
        Apply network-aware multiplier to delay.

        Args:
            base_delay: Base delay before network adjustment
            config: Backoff configuration
            network_health_monitor: Network health monitor instance
            service_name: Service name for logging

        Returns:
            Adjusted delay
        """
        if network_health_monitor and not network_health_monitor.is_network_healthy():
            if (
                network_health_monitor.is_network_degraded()
                or network_health_monitor.is_network_offline()
            ):
                adjusted_delay = base_delay * config.network_degraded_multiplier
                logger.debug(
                    f"[BackoffManager] Applied network degraded multiplier ({config.network_degraded_multiplier}x) for {service_name}"
                )
                return adjusted_delay
        return base_delay

    @staticmethod
    def apply_jitter(base_delay: float, jitter_range: float) -> float:
        """
        Apply jitter to prevent thundering herd.

        Args:
            base_delay: Base delay
            jitter_range: Jitter range as fraction of base delay

        Returns:
            Delay with jitter applied
        """
        jitter_amount = base_delay * jitter_range
        jitter = backoff_random.uniform(-jitter_amount, jitter_amount)
        return max(0.1, base_delay + jitter)  # Ensure minimum delay

    @classmethod
    def calculate_full_delay(
        cls,
        config: BackoffConfig,
        attempt: int,
        network_health_monitor,
        service_name: str,
    ) -> float:
        """
        Calculate complete delay with all adjustments.

        Args:
            config: Backoff configuration
            attempt: Attempt number
            network_health_monitor: Network health monitor
            service_name: Service name for logging

        Returns:
            Final delay in seconds
        """
        base_delay = cls.calculate_base_delay(config, attempt)
        network_adjusted = cls.apply_network_multiplier(
            base_delay, config, network_health_monitor, service_name
        )
        final_delay = cls.apply_jitter(network_adjusted, config.jitter_range)

        logger.debug(
            f"[BackoffManager] Calculated backoff for {service_name}: "
            f"attempt={attempt}, base_delay={base_delay:.2f}s, final_delay={final_delay:.2f}s"
        )

        return final_delay
