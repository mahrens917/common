"""Fills data fetching."""

import logging
from typing import Any, Dict, List, Optional

from ....trading_exceptions import KalshiAPIError
from ...constants import CLIENT_API_ERRORS

logger = logging.getLogger(__name__)


class FillsFetcher:
    """Fetch order fills data from Kalshi API."""

    def __init__(self, kalshi_client):
        self._client = kalshi_client

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Fetch fills for a specific order."""
        try:
            return await self._client.get_fills(order_id)
        except CLIENT_API_ERRORS as exc:
            logger.exception(
                "[KalshiTradingClient] Failed to get fills for order %s (%s)",
                order_id,
                type(exc).__name__,
            )
            raise KalshiAPIError(f"Failed to get fills") from exc

    async def get_all_fills(
        self,
        min_ts: Optional[int],
        max_ts: Optional[int],
        ticker: Optional[str],
        cursor: Optional[str],
    ) -> Dict[str, Any]:
        """Fetch all fills subject to optional filters."""
        try:
            return await self._client.get_all_fills(min_ts, max_ts, ticker, cursor)
        except CLIENT_API_ERRORS as exc:
            logger.exception(
                "[KalshiTradingClient] Failed to get all fills (%s)",
                type(exc).__name__,
            )
            raise KalshiAPIError(f"Failed to get all fills") from exc
