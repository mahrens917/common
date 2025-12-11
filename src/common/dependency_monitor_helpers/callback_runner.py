"""Callback execution utilities for dependency monitor."""

import asyncio
import logging
from typing import Callable, List

logger = logging.getLogger(__name__)


class CallbackRunner:
    """Handles running callbacks with error handling."""

    @staticmethod
    async def run_callbacks(callbacks: List[Callable], service_name: str, callback_executor) -> None:
        """Run list of callbacks."""
        for callback in callbacks:
            try:
                error = await callback_executor.run_callback(callback)
            except asyncio.CancelledError:
                raise
            except (RuntimeError, ValueError, TypeError, AttributeError, Exception):
                logger.exception("[%s] Error in callback", service_name)
                continue
            if isinstance(error, BaseException):
                logger.error("[%s] Error in callback: %s", service_name, error)
