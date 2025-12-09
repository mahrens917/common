from __future__ import annotations

"""Redis connection helper exports without circular imports."""

import logging
from typing import Awaitable, Callable


async def ensure_or_raise(
    check_connection: Callable[[], Awaitable[bool]],
    *,
    operation: str,
    logger: logging.Logger,
) -> None:
    """
    Ensure a Redis connection is available or raise a RuntimeError.

    Args:
        check_connection: Awaitable that returns a boolean indicating readiness.
        operation: Description of the attempted operation.
        logger: Logger used for diagnostics.
    """
    ok = await check_connection()
    if ok:
        return

    error_msg = f"Failed to ensure Redis connection for {operation}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)


__all__ = ["ensure_or_raise"]
