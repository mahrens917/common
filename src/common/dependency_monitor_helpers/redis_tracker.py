"""Redis dependency tracking for dependency monitor."""

import logging
from typing import Awaitable, List, Optional, cast

from redis.asyncio import Redis

from .dependency_checker import DependencyStatus

logger = logging.getLogger(__name__)


async def _capture_async_result(awaitable):
    import asyncio

    (result,) = await asyncio.gather(awaitable, return_exceptions=True)
    if isinstance(result, BaseException):
        return None, result
    return result, None


class RedisTracker:
    """Manages Redis tracking for dependency statuses."""

    def __init__(self, service_name: str, redis: Optional[Redis]):
        self.service_name = service_name
        self.redis = redis

    async def initialize_dependency_tracking(self, dependency_names: List[str]) -> None:
        if not self.redis or not dependency_names:
            return

        dependencies_key = f"service_dependencies:{self.service_name}"
        _, delete_error = await _capture_async_result(self.redis.delete(dependencies_key))
        if isinstance(delete_error, BaseException):
            logger.error("[%s] Failed to clear dependency list in Redis: %s", self.service_name, delete_error)
            return

        _, add_error = await _capture_async_result(cast(Awaitable[int], self.redis.sadd(dependencies_key, *dependency_names)))
        if isinstance(add_error, BaseException):
            logger.error("[%s] Failed to seed dependency list in Redis: %s", self.service_name, add_error)
            return

        status_key = f"dependency_status:{self.service_name}"
        for dep_name in dependency_names:
            _, set_error = await _capture_async_result(
                cast(
                    Awaitable[int],
                    self.redis.hset(status_key, dep_name, DependencyStatus.UNKNOWN.value),
                )
            )
            if isinstance(set_error, BaseException):
                logger.error(
                    "[%s] Failed to initialize dependency status for %s: %s",
                    self.service_name,
                    dep_name,
                    set_error,
                )
                return

        logger.debug("[%s] Initialized dependency tracking for: %s", self.service_name, dependency_names)

    async def update_dependency_status(self, dependency_name: str, status: DependencyStatus) -> None:
        if not self.redis:
            return

        status_key = f"dependency_status:{self.service_name}"
        _, error = await _capture_async_result(cast(Awaitable[int], self.redis.hset(status_key, dependency_name, status.value)))
        if isinstance(error, BaseException):
            logger.error("[%s] Failed to update dependency status in Redis: %s", self.service_name, error)
            return

        logger.debug(
            "[%s] Updated Redis dependency status: %s = %s",
            self.service_name,
            dependency_name,
            status.value,
        )
