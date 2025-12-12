"""Market data scanner for lifecycle monitoring."""

import asyncio
import logging
from typing import Any, Dict, Optional

from ..kalshi_trading_client import KalshiTradingClient
from ..trading_exceptions import KalshiTradingError

logger = logging.getLogger(__name__)

TRADING_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


class MarketScanner:
    """Scans market data from Kalshi API."""

    def __init__(self, trading_client: KalshiTradingClient):
        """
        Initialize market scanner.

        Args:
            trading_client: Trading client for API access
        """
        self.trading_client = trading_client

    async def fetch_market_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch market data from API.

        Args:
            ticker: Market ticker to fetch

        Returns:
            Market data dict or None if not found
        """
        try:
            response = await self.trading_client.kalshi_client.api_request(
                method="GET",
                path=f"/trade-api/v2/markets/{ticker}",
                params={},
                operation_name="get_market_info",
            )
            if not response:
                return None
            return response["market"] if "market" in response else None

        except TRADING_ERRORS:  # policy_guard: allow-silent-handler
            logger.exception(f"[MarketScanner] Error fetching market data for : ")
            return None
