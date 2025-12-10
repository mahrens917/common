from __future__ import annotations

"""
Trade collection lifecycle helpers.
"""


import logging
from typing import Awaitable, Callable

from common.exceptions import ValidationError

from ...redis_protocol.trade_store import TradeStore


class TradeCollectionController:
    """Thin wrapper that validates trade store readiness for collection loops."""

    def __init__(
        self,
        *,
        trade_store_getter: Callable[[], Awaitable[TradeStore]],
        logger: logging.Logger,
    ) -> None:
        self._trade_store_getter = trade_store_getter
        self._logger = logger

    async def start(self) -> None:
        """Ensure a trade store is available before marking collection as active."""
        try:
            await self._trade_store_getter()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            raise ValidationError("Trade store required for trade collection") from exc

        self._logger.info("[KalshiTradingClient] Trade collection started (immediate storage mode)")

    async def stop(self) -> None:
        """Mark collection as inactive."""
        self._logger.info("[KalshiTradingClient] Trade collection stopped")


__all__ = ["TradeCollectionController"]
