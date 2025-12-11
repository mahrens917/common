"""Connection retry coordination logic."""

import logging
from typing import Any, Callable, Optional

from redis.exceptions import RedisError

from ..connection_state import ConnectionState
from ..connection_state_tracker import ConnectionStateTrackerError


class RetryCoordinator:
    """Coordinates connection retry attempts with backoff."""

    def __init__(
        self,
        service_name: str,
        state_manager: Any,
        metrics_tracker: Any,
        reconnection_handler: Any,
        lifecycle_manager: Any,
        notification_handler: Any,
        max_consecutive_failures: int,
    ):
        """Initialize retry coordinator."""
        self.service_name = service_name
        self.state_manager = state_manager
        self.metrics_tracker = metrics_tracker
        self.reconnection_handler = reconnection_handler
        self.lifecycle_manager = lifecycle_manager
        self.notification_handler = notification_handler
        self.max_consecutive_failures = max_consecutive_failures
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def _transition_state(self, new_state: ConnectionState, error_context: Optional[str] = None) -> None:
        """Transition to a new connection state."""
        self.state_manager.transition_state(new_state, error_context)

        if new_state == ConnectionState.CONNECTED:
            self.metrics_tracker.record_success()
        elif new_state == ConnectionState.FAILED:
            self.metrics_tracker.record_failure()

    async def _send_notification(self, is_connected: bool, details: str = "") -> None:
        """Send connection notification."""
        await self.notification_handler.send_connection_notification(is_connected, details)

    async def connect_with_retry(self, establish_connection: Callable[[], Any]) -> bool:
        """Attempt connection with exponential backoff retry logic."""
        self.logger.info(f"Starting connection attempt for {self.service_name}")

        while self.reconnection_handler.should_retry() and not self.lifecycle_manager.shutdown_requested:
            attempt_number = self.metrics_tracker.get_metrics().total_reconnection_attempts + 1

            try:
                await self.reconnection_handler.apply_backoff()

                if self.lifecycle_manager.shutdown_requested:
                    self.logger.info("Shutdown requested, aborting connection attempt")
                    return False

                metrics = self.metrics_tracker.get_metrics()
                if metrics.consecutive_failures == 1:
                    await self._send_notification(is_connected=False, details="Connection lost")

                self._transition_state(ConnectionState.CONNECTING)
                connection_successful = await establish_connection()
                self.metrics_tracker.metrics.total_reconnection_attempts = attempt_number

                if connection_successful:
                    self.metrics_tracker.increment_total_connections()
                    self._transition_state(ConnectionState.READY)
                    self.logger.info(f"Successfully connected {self.service_name}")
                    await self._send_notification(
                        is_connected=True,
                        details=f"Connection restored after {attempt_number} attempts",
                    )
                    return True
                else:
                    self._transition_state(ConnectionState.FAILED, "Connection establishment failed")
                    self.logger.warning(f"Connection attempt failed for {self.service_name}")

            except (
                ConnectionError,
                TimeoutError,
                ConnectionStateTrackerError,
                RedisError,
                RuntimeError,
            ) as e:
                self.metrics_tracker.metrics.total_reconnection_attempts = attempt_number
                self._transition_state(ConnectionState.FAILED, str(e))
                self.logger.exception(f"Connection attempt failed with exception: ")
                if not self.reconnection_handler.should_retry():
                    raise

        self.logger.error(f"Failed to connect {self.service_name} after {self.max_consecutive_failures} attempts")
        return False
