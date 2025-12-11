"""Registration methods for StatusReporterMixin."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..status_reporter_mixin import StatusReporterMixin


async def register_startup(reporter: "StatusReporterMixin") -> None:
    """Report that service is starting up (INITIALIZING state)."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.INITIALIZING)


async def register_shutdown(reporter: "StatusReporterMixin") -> None:
    """Report that service is shutting down."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.STOPPING)
    await reporter.report_status(ServiceStatus.STOPPED)


async def register_ready(reporter: "StatusReporterMixin", **metrics: Any) -> None:
    """Report that service is fully operational (READY state)."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.READY, **metrics)


async def register_ready_degraded(reporter: "StatusReporterMixin", reason: str, **metrics: Any) -> None:
    """Report that service is operational but degraded."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.READY_DEGRADED, degraded_reason=reason, **metrics)


async def register_error(reporter: "StatusReporterMixin", error_message: str, **context: Any) -> None:
    """Report that service encountered an error."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.ERROR, error=error_message, **context)


async def register_failed(reporter: "StatusReporterMixin", failure_message: str, **context: Any) -> None:
    """Report that service has failed and cannot continue."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.FAILED, failure_reason=failure_message, **context)


async def register_starting(reporter: "StatusReporterMixin", **context: Any) -> None:
    """Report that service is in STARTING state (awaiting dependencies)."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.STARTING, **context)


async def register_restarting(reporter: "StatusReporterMixin", reason: str) -> None:
    """Report that service is being restarted."""
    from common.service_status import ServiceStatus

    await reporter.report_status(ServiceStatus.RESTARTING, restart_reason=reason)


__all__ = [
    "register_startup",
    "register_shutdown",
    "register_ready",
    "register_ready_degraded",
    "register_error",
    "register_failed",
    "register_starting",
    "register_restarting",
]
