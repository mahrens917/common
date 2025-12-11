"""Standardized status reporting mixin for all services."""

import logging
import os
import time
from typing import Any, Optional

from redis.asyncio import Redis

from common.redis_schema.operations import ServiceStatusKey

logger = logging.getLogger(__name__)


class StatusReporterMixin:
    """Mixin providing standardized status reporting to Redis for all services."""

    def __init__(self, service_name: str, redis_client: Optional[Redis] = None):
        """Initialize status reporter mixin."""
        self._service_name, self._redis_client, self._redis_client_cached = (
            service_name,
            redis_client,
            None,
        )
        self._status_key, self._start_time, self._pid = (
            ServiceStatusKey(service=service_name).key(),
            time.time(),
            os.getpid(),
        )
        logger.debug(
            "StatusReporterMixin initialized",
            extra={"service": service_name, "pid": self._pid, "status_key": self._status_key},
        )

    async def _get_redis_client(self) -> Redis:
        """Get Redis client, creating one if necessary."""
        from .status_reporter_helpers.redis_client_manager import get_redis_client_for_reporter

        if self._redis_client_cached is None:
            self._redis_client_cached = await get_redis_client_for_reporter(self._redis_client, self._redis_client_cached)
        return self._redis_client_cached if self._redis_client is None else self._redis_client

    async def report_status(self, status, **additional_fields: Any) -> None:
        """Report service status to Redis using unified pattern."""
        from .status_reporter_helpers.status_writer import write_status_to_redis

        redis = await self._get_redis_client()
        await write_status_to_redis(
            redis,
            self._status_key,
            self._service_name,
            status,
            self._pid,
            self._start_time,
            additional_fields,
        )

    async def register_startup(self) -> None:
        from .status_reporter_helpers.registration_methods import register_startup as rs

        await rs(self)

    async def register_shutdown(self) -> None:
        from .status_reporter_helpers.registration_methods import register_shutdown as rd

        await rd(self)

    async def register_ready(self, **metrics: Any) -> None:
        from .status_reporter_helpers.registration_methods import register_ready as rr

        await rr(self, **metrics)

    async def register_ready_degraded(self, reason: str, **metrics: Any) -> None:
        from .status_reporter_helpers.registration_methods import register_ready_degraded as rrd

        await rrd(self, reason, **metrics)

    async def register_error(self, error_message: str, **context: Any) -> None:
        from .status_reporter_helpers.registration_methods import register_error as re

        await re(self, error_message, **context)

    async def register_failed(self, failure_message: str, **context: Any) -> None:
        from .status_reporter_helpers.registration_methods import register_failed as rf

        await rf(self, failure_message, **context)

    async def register_starting(self, **context: Any) -> None:
        from .status_reporter_helpers.registration_methods import register_starting as rst

        await rst(self, **context)

    async def register_restarting(self, reason: str) -> None:
        from .status_reporter_helpers.registration_methods import register_restarting as rrt

        await rrt(self, reason)

    service_name = property(lambda self: self._service_name)
    status_key = property(lambda self: self._status_key)
    uptime_seconds = property(lambda self: time.time() - self._start_time)
