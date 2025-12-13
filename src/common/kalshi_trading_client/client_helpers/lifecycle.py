from __future__ import annotations

"""Client lifecycle management (initialize, close, context manager)."""


import logging
from typing import TYPE_CHECKING

from ..constants import CLEANUP_ERRORS

if TYPE_CHECKING:
    from common.trading import TradeStoreManager
    from src.kalshi.api.client import KalshiClient

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages client lifecycle operations."""

    @staticmethod
    async def initialize(kalshi_client: KalshiClient) -> None:
        """Initialize the trading client and underlying connections."""
        await kalshi_client.initialize()
        logger.info("[KalshiTradingClient] Trading client initialized successfully")

    @staticmethod
    async def close(kalshi_client: KalshiClient, trade_store_manager: TradeStoreManager) -> None:
        """Close client connections and cleanup resources."""
        try:
            await kalshi_client.close()
            logger.info("[KalshiTradingClient] Trading client closed")
        except CLEANUP_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.warning(
                "[KalshiTradingClient] Error during close (%s): %s",
                type(exc).__name__,
                str(exc),
            )
        await trade_store_manager.close_managed()

    @staticmethod
    def log_context_exit(exc_type, exc_val, exc_tb) -> bool:
        """Log context manager exit and return whether to suppress exception."""
        if exc_type is not None:
            logger.warning(
                f"[KalshiTradingClient] Exception in context manager: {exc_type.__name__}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb),
            )
        return False
