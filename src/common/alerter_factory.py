from __future__ import annotations

"""Factories for creating alerter instances with safe shutdown guarantees."""

import asyncio
import atexit
import logging
import weakref

logger = logging.getLogger(__name__)

try:
    from src.monitor.alerter import Alerter as ServiceAlerter
except ImportError as exc:
    logger.debug("Monitor module not available, using fallback: %s", exc)

    class ServiceAlerter:  # type: ignore
        """Fallback alerter for repos without monitor module."""

        async def alert(self, *args, **kwargs):  # type: ignore
            """No-op alert method."""
            pass


_shutdown_registry: "weakref.WeakSet" = weakref.WeakSet()


class AlerterCleanupError(RuntimeError):
    """Raised when the alerter cleanup sequence fails."""


def _register_shutdown_hook(alerter) -> None:
    """Ensure alerter cleanup runs even if the hosting service crashes early."""

    if alerter in _shutdown_registry:
        return

    _shutdown_registry.add(alerter)

    def _cleanup() -> None:
        from redis.exceptions import RedisError
        from src.monitor.alerting.models import AlerterError

        from common.redis_utils import RedisOperationError

        cleanup_errors = (
            AlerterError,
            asyncio.TimeoutError,
            RedisError,
            RedisOperationError,
            OSError,
        )

        try:
            asyncio.run(alerter.cleanup())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(alerter.cleanup())
            except cleanup_errors as exc:  # pragma: no cover - defensive logging
                logger.warning("Alerter cleanup during interpreter shutdown failed: %s", exc, exc_info=True)
                raise AlerterCleanupError("Alerter cleanup failed during interpreter shutdown") from exc
            finally:
                loop.close()
        except cleanup_errors as exc:  # pragma: no cover - defensive logging
            logger.warning("Alerter cleanup during interpreter shutdown failed: %s", exc, exc_info=True)
            raise AlerterCleanupError("Alerter cleanup failed during interpreter shutdown") from exc

    atexit.register(_cleanup)


def create_alerter() -> ServiceAlerter:
    """
    Factory function to create new Alerter instance.

    Creates a fresh Alerter instance for each call, avoiding singleton
    pattern issues in multiprocessing environments. Each process gets
    its own Alerter instance with independent state.

    Returns:
        Alerter: New Alerter instance configured from environment variables

    Example:
        >>> alerter = create_alerter()
        >>> await alerter.send_alert("Test message", AlertSeverity.INFO)
    """
    alerter = ServiceAlerter()
    logger.debug("Created new Alerter instance via factory")
    _register_shutdown_hook(alerter)
    return alerter


def create_alerter_for_service(service_name: str) -> ServiceAlerter:
    """
    Factory function to create Alerter instance with service context.

    Creates an Alerter instance and logs which service is using it
    for better debugging and monitoring.

    Args:
        service_name: Name of the service creating the alerter

    Returns:
        Alerter: New Alerter instance

    Example:
        >>> alerter = create_alerter_for_service("price_alert")
    """
    alerter = create_alerter()
    logger.info("Created Alerter instance for service: %s", service_name)
    return alerter
