"""
Distributed locking utility using Redis for preventing race conditions.

This module provides a simple, robust distributed lock implementation using Redis
SET NX EX commands for atomic lock acquisition with automatic expiration.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from ..redis_protocol.error_types import REDIS_ERRORS
from .distributed_lock_errors import LockUnavailableError

logger = logging.getLogger(__name__)


class DistributedLock:
    """Redis-based distributed lock using SET NX EX for atomic acquisition."""

    def __init__(self, redis_client, lock_key: str, timeout_seconds: int = 30):
        """Initialize distributed lock with Redis client, key, and timeout."""
        self.redis_client = redis_client
        self.lock_key = lock_key
        self.timeout_seconds = timeout_seconds
        self.lock_value = f"{os.getpid()}:{time.time()}"
        self._acquired = False

    async def acquire(self) -> bool:
        """Attempt to acquire the distributed lock. Raises LockUnavailableError if unavailable."""
        if not self.redis_client:
            raise LockUnavailableError(
                f"Redis client is required to acquire distributed lock '{self.lock_key}'"
            )

        try:
            # Use SET NX EX for atomic lock acquisition with expiration
            lock_acquired = await self.redis_client.set(
                self.lock_key,
                self.lock_value,
                ex=self.timeout_seconds,  # Auto-expire to prevent deadlocks
                nx=True,  # Only set if key doesn't exist
            )
        except REDIS_ERRORS as exc:
            raise LockUnavailableError(
                f"Failed to acquire distributed lock '{self.lock_key}': {exc}"
            ) from exc

        if not lock_acquired:
            raise LockUnavailableError(
                f"Distributed lock '{self.lock_key}' is already held by another process"
            )

        self._acquired = True
        logger.debug(f"Acquired distributed lock: {self.lock_key}")
        return True

    async def release(self) -> None:
        """Release the distributed lock if we own it. Raises LockUnavailableError if unsafe."""
        if not self.redis_client:
            raise LockUnavailableError(
                f"Redis client is required to release distributed lock '{self.lock_key}'"
            )

        if not self._acquired:
            raise LockUnavailableError(
                f"Distributed lock '{self.lock_key}' cannot be released because it was not acquired"
            )

        try:
            current_value = await self.redis_client.get(self.lock_key)
            if current_value is None:
                raise LockUnavailableError(
                    f"Distributed lock '{self.lock_key}' expired or was cleared externally"
                )

            if current_value != self.lock_value:
                raise LockUnavailableError(
                    f"Distributed lock '{self.lock_key}' is held by another owner"
                )

            await self.redis_client.delete(self.lock_key)
            self._acquired = False
            logger.debug(f"Released distributed lock: {self.lock_key}")

        except REDIS_ERRORS as exc:
            raise LockUnavailableError(
                f"Failed to release distributed lock '{self.lock_key}': {exc}"
            ) from exc

    @asynccontextmanager
    async def acquire_context(self):
        """Context manager for automatic lock acquisition and release."""
        try:
            acquired = await self.acquire()
        except (LockUnavailableError, RuntimeError, ValueError) as exc:
            raise LockUnavailableError(f"Could not acquire lock: {self.lock_key}") from exc

        if not acquired:
            raise LockUnavailableError(f"Could not acquire lock: {self.lock_key}")

        try:
            yield
        finally:
            await self.release()


async def create_trade_lock(
    redis_client, trade_id: str, timeout_seconds: int = 30
) -> DistributedLock:
    """Create a distributed lock for trade execution."""
    lock_key = f"trade_lock:{trade_id}"
    return DistributedLock(redis_client, lock_key, timeout_seconds)


async def create_liquidation_lock(
    redis_client, position_id: str, timeout_seconds: int = 60
) -> DistributedLock:
    """Create a distributed lock for position liquidation."""
    lock_key = f"liquidation_lock:{position_id}"
    return DistributedLock(redis_client, lock_key, timeout_seconds)


__all__ = [
    "DistributedLock",
    "LockUnavailableError",
    "create_trade_lock",
    "create_liquidation_lock",
]
