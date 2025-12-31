"""Health check execution logic."""

import logging
import time
from typing import Protocol, Set

logger = logging.getLogger(__name__)
_MISSING_TIMESTAMP = object()


class WebSocketClient(Protocol):
    """Protocol for WebSocket client interface."""

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        ...

    @property
    def active_subscriptions(self) -> Set[str]:
        """Get active subscriptions."""
        ...


class SubscriptionManager(Protocol):
    """Protocol for subscription manager interface."""

    @property
    def active_instruments(self) -> dict:
        """Get dictionary of active instruments."""
        ...


class StatsCollector(Protocol):
    """Protocol for stats collector interface."""

    @property
    def current_rate(self) -> int:
        """Get current message rate."""
        ...

    @property
    def last_nonzero_update_time(self) -> float:
        """Get timestamp of last non-zero update."""
        ...


class HealthChecker:
    """Executes comprehensive health checks."""

    def __init__(
        self,
        service_name: str,
        websocket_client: WebSocketClient,
        subscription_manager: SubscriptionManager,
        stats_collector: StatsCollector,
        max_silent_duration_seconds: int,
    ):
        """
        Initialize health checker.

        Args:
            service_name: Name of the service
            websocket_client: WebSocket client instance
            subscription_manager: Subscription manager instance
            stats_collector: Statistics collector instance
            max_silent_duration_seconds: Max seconds without data before failure
        """
        self.service_name = service_name
        self.websocket_client = websocket_client
        self.subscription_manager = subscription_manager
        self.stats_collector = stats_collector
        self.max_silent_duration_seconds = max_silent_duration_seconds

    def check_connection_status(self) -> None:
        if not self.websocket_client.is_connected:
            error_msg = f"{self.service_name} WebSocket not connected"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

    def check_subscription_status(self) -> None:
        subscription_count = len(self.subscription_manager.active_instruments)
        websocket_subscription_count = len(self.websocket_client.active_subscriptions)
        if subscription_count == 0 and websocket_subscription_count == 0:
            error_msg = f"{self.service_name} has no active subscriptions - zombie state"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

    def check_data_flow(self, current_time: float) -> float:
        last_time = self._resolve_last_update_time()
        time_since_last_data = current_time - last_time
        if time_since_last_data > self.max_silent_duration_seconds:
            error_msg = f"{self.service_name} no data flow for {time_since_last_data:.1f}s - zombie state"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        return time_since_last_data

    def log_health_check_passed(self, time_since_data: float) -> None:
        logger.debug(
            f"{self.service_name} health check passed: "
            f"connected={self.websocket_client.is_connected}, "
            f"subscriptions={len(self.subscription_manager.active_instruments)}, "
            f"ws_subscriptions={len(self.websocket_client.active_subscriptions)}, "
            f"current_rate={self.stats_collector.current_rate}, "
            f"time_since_data={time_since_data:.1f}s"
        )

    def is_healthy_sync(self) -> bool:
        try:
            if not self.websocket_client.is_connected:
                return False
            if len(self.subscription_manager.active_instruments) == 0:
                return False
            current_time = time.time()
            last_time = self._resolve_last_update_time()
            time_since_last_data = current_time - last_time
            if time_since_last_data > self.max_silent_duration_seconds:
                return False
            else:
                return True
        except (
            RuntimeError,
            AttributeError,
            ValueError,
        ):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.exception("Error in %s health check", self.service_name)
            return False

    def _resolve_last_update_time(self) -> float:
        if hasattr(self.stats_collector, "_last_nonzero_update_time"):
            value = getattr(self.stats_collector, "_last_nonzero_update_time")
        else:
            value = getattr(self.stats_collector, "last_nonzero_update_time", _MISSING_TIMESTAMP)
            if value is _MISSING_TIMESTAMP:
                value = 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (TypeError, ValueError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                logger.warning("Failed to parse health stat as float: value=%r, error=%s", value, exc)
                return 0.0
        return 0.0
