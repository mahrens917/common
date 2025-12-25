"""Dependency status checking."""

from __future__ import annotations

import logging
from typing import List

from redis.asyncio import Redis

from ..redis_protocol.typing import ensure_awaitable

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Checks dependency availability status."""

    @staticmethod
    async def get_service_dependencies(redis: Redis, service_name: str) -> List[str]:
        """Get list of dependencies for a service from Redis.

        Raises:
            ConnectionError: If Redis connection fails
            OSError: If system-level error occurs
            RuntimeError: If runtime error occurs during Redis operation
        """
        dependencies_key = f"service_dependencies:{service_name}"
        try:
            dependencies = await ensure_awaitable(redis.smembers(dependencies_key))
        except (ConnectionError, OSError, RuntimeError):  # Transient network/connection failure  # policy_guard: allow-silent-handler
            logger.exception("Failed to get dependencies for %s", service_name)
            return []
        return [dep.decode("utf-8") if isinstance(dep, bytes) else dep for dep in dependencies]

    @staticmethod
    async def is_dependency_unavailable(redis: Redis, service_name: str, dependency_name: str, redis_key_prefix: str) -> bool:
        """Check if a specific dependency is currently unavailable.

        Raises:
            ConnectionError: If Redis connection fails
            OSError: If system-level error occurs
            RuntimeError: If runtime error occurs during Redis operation
        """
        status_key = f"{redis_key_prefix}:{service_name}"
        try:
            status = await ensure_awaitable(redis.hget(status_key, dependency_name))
        except (ConnectionError, OSError, RuntimeError):  # Transient network/connection failure  # policy_guard: allow-silent-handler
            logger.exception(
                "Failed to check dependency status for %s:%s",
                service_name,
                dependency_name,
            )
            return False

        if status is None:
            _none_guard_value = False
            return _none_guard_value

        status_str = status.decode("utf-8") if isinstance(status, bytes) else status
        return status_str.lower() in ("unavailable", "unknown", "failed")
