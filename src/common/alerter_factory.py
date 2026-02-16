from __future__ import annotations

"""Factories for creating alerter instances with safe shutdown guarantees."""

import asyncio
import atexit
import logging
import weakref
from typing import Protocol

logger = logging.getLogger(__name__)


class ServiceAlerterProtocol(Protocol):
    async def cleanup(self) -> None: ...


ServiceAlerter: type[ServiceAlerterProtocol]


try:
    from common.alerter import Alerter as ServiceAlerter
except ImportError as exc:  # Optional module not available  # policy_guard: allow-silent-handler
    logger.debug("Monitor module not available, using stub: %s", exc)

    class _StubAlerter:
        """Stub alerter for repos without monitor module."""

        async def cleanup(self) -> None:
            """No-op cleanup method."""
            return None

    ServiceAlerter = _StubAlerter


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

        from common.redis_utils import RedisOperationError

        alert_errors = []
        try:
            from common.alerting.models import AlerterError as CommonAlerterError  # type: ignore

            alert_errors.append(CommonAlerterError)
        except ImportError as e:  # Optional module not available  # policy_guard: allow-silent-handler
            logger.debug("CommonAlerterError not available: %s", e)

        try:
            from src.monitor.alerting.models import AlerterError as MonitorAlerterError  # type: ignore

            alert_errors.append(MonitorAlerterError)
        except ImportError as e:  # Optional module not available  # policy_guard: allow-silent-handler
            logger.debug("MonitorAlerterError not available: %s", e)

        cleanup_errors = (asyncio.TimeoutError, RedisError, RedisOperationError, OSError)
        if alert_errors:
            cleanup_errors = tuple(alert_errors) + cleanup_errors

        try:
            asyncio.run(alerter.cleanup())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(alerter.cleanup())
            except cleanup_errors as exc:
                logger.warning("Alerter cleanup during interpreter shutdown failed: %s", exc, exc_info=True)
                raise AlerterCleanupError("Alerter cleanup failed during interpreter shutdown") from exc
            finally:
                loop.close()
        except cleanup_errors as exc:
            logger.warning("Alerter cleanup during interpreter shutdown failed: %s", exc, exc_info=True)
            raise AlerterCleanupError("Alerter cleanup failed during interpreter shutdown") from exc

    atexit.register(_cleanup)


def create_alerter() -> ServiceAlerterProtocol:
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


def create_alerter_for_service(service_name: str) -> ServiceAlerterProtocol:
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
