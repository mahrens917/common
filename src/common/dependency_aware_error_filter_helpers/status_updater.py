"""Dependency status update operations."""

from __future__ import annotations

import logging
from typing import List

from redis.asyncio import Redis

from ..redis_protocol.typing import ensure_awaitable

logger = logging.getLogger(__name__)


class StatusUpdater:
    """Updates dependency status in Redis."""

    @staticmethod
    async def update_service_dependencies(redis: Redis, service_name: str, dependencies: List[str]) -> None:
        """Update the dependency list for a service in Redis.

        Raises:
            ConnectionError: If Redis connection fails
            OSError: If system-level error occurs
            RuntimeError: If runtime error occurs during Redis operation
        """
        dependencies_key = f"service_dependencies:{service_name}"
        try:
            await ensure_awaitable(redis.delete(dependencies_key))
            if dependencies:
                await ensure_awaitable(redis.sadd(dependencies_key, *dependencies))
            logger.debug("Updated dependencies for %s: %s", service_name, dependencies)
        except (ConnectionError, OSError, RuntimeError):
            logger.exception("Failed to update dependencies for %s", service_name)

    @staticmethod
    async def update_dependency_status(redis: Redis, service_name: str, dependency_name: str, status: str, redis_key_prefix: str) -> None:
        """Update the status of a specific dependency in Redis.

        Raises:
            ConnectionError: If Redis connection fails
            OSError: If system-level error occurs
            RuntimeError: If runtime error occurs during Redis operation
        """
        status_key = f"{redis_key_prefix}:{service_name}"
        try:
            await ensure_awaitable(redis.hset(status_key, dependency_name, status))
            logger.debug("Updated dependency status: %s:%s = %s", service_name, dependency_name, status)
        except (ConnectionError, OSError, RuntimeError):
            logger.exception(
                "Failed to update dependency status for %s:%s",
                service_name,
                dependency_name,
            )
