"""State accessor properties for KalshiRateLimiter.

This module provides property definitions that are mixed into KalshiRateLimiter
to reduce class size.
"""

import asyncio
from typing import Any, Optional

from .token_manager import TokenManager
from .worker_manager import WorkerManager


class StateAccessorsMixin:
    """Mixin providing state accessor properties for rate limiter."""

    worker_manager: WorkerManager
    token_manager: TokenManager

    @property
    def _shutdown_event(self) -> asyncio.Event:
        """Access shutdown event."""
        return self.worker_manager.shutdown_event

    @property
    def _worker_task(self) -> Optional[asyncio.Task[Any]]:
        """Access worker task."""
        return self.worker_manager.worker_task

    @_worker_task.setter
    def _worker_task(self, value: Optional[asyncio.Task[Any]]) -> None:
        """Set worker task."""
        self.worker_manager.worker_task = value

    @property
    def read_tokens(self) -> int:
        """Access read tokens."""
        return self.token_manager.read_tokens

    @read_tokens.setter
    def read_tokens(self, value: int) -> None:
        """Set read tokens."""
        self.token_manager.read_tokens = value

    @property
    def write_tokens(self) -> int:
        """Access write tokens."""
        return self.token_manager.write_tokens

    @write_tokens.setter
    def write_tokens(self, value: int) -> None:
        """Set write tokens."""
        self.token_manager.write_tokens = value
