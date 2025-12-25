"""Order metadata fetching with error handling."""

import logging
from typing import Any, Awaitable, Callable, Tuple

from ....redis_protocol.trade_store import TradeStore, TradeStoreError
from ....trading.order_metadata_service import fetch_order_metadata
from ....trading_exceptions import KalshiDataIntegrityError
from ...constants import TELEGRAM_ALERT_ERRORS

logger = logging.getLogger(__name__)


class MetadataFetcher:
    """Fetch order metadata with comprehensive error handling."""

    def __init__(self, trade_store_getter: Callable[[], Awaitable[TradeStore]], telegram_handler=None):
        self._get_trade_store = trade_store_getter
        self._telegram_handler = telegram_handler

    def set_telegram_handler(self, handler: Any) -> None:
        """Update the telegram handler used for metadata error alerts."""
        self._telegram_handler = handler

    async def get_trade_metadata_from_order(self, order_id: str) -> Tuple[str, str]:
        """
        Lookup stored order metadata and fail-fast when unavailable.

        Returns:
            Tuple of (trade_rule, trade_reason)

        Raises:
            KalshiDataIntegrityError: If metadata cannot be retrieved
        """
        try:
            return await fetch_order_metadata(order_id, self._get_trade_store, self._telegram_handler, logger)
        except KalshiDataIntegrityError:
            raise
        except (TradeStoreError, ValueError, TypeError, RuntimeError) as exc:
            error_msg = f"CRITICAL: Failed to retrieve order metadata for trade rule determination. " f"Order ID: {order_id}, Error"
            logger.exception(error_msg)

            if self._telegram_handler:
                try:
                    await self._telegram_handler.send_alert(
                        f"🚨 ORDER METADATA LOOKUP FAILURE\n\n{error_msg}\n\nThis requires immediate investigation."
                    )
                except TELEGRAM_ALERT_ERRORS as telegram_error:  # Expected exception in operation  # policy_guard: allow-silent-handler
                    logger.exception(
                        "Failed to send telegram alert (%s)",
                        type(telegram_error).__name__,
                    )

            raise KalshiDataIntegrityError(error_msg) from exc
