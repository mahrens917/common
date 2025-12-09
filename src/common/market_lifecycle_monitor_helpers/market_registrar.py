"""Market registration handler."""

import asyncio
import logging
from typing import Optional

from ..trading_exceptions import KalshiTradingError
from .market_scanner import MarketScanner
from .notification_sender import NotificationSender
from .state_tracker import MarketInfo, StateTracker

logger = logging.getLogger(__name__)

TRADING_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


class MarketRegistrar:
    """Handles market registration for monitoring."""

    def __init__(
        self, scanner: MarketScanner, state_tracker: StateTracker, notifier: NotificationSender
    ):
        """
        Initialize market registrar.

        Args:
            scanner: Market scanner for data fetching
            state_tracker: State tracker for storing market info
            notifier: Notification sender for logging
        """
        self.scanner = scanner
        self.state_tracker = state_tracker
        self.notifier = notifier

    async def register_market(self, ticker: str) -> Optional[MarketInfo]:
        """
        Register a market for lifecycle monitoring.

        Args:
            ticker: Market ticker to monitor

        Returns:
            MarketInfo if successfully registered, None if market not found
        """
        try:
            market_data = await self.scanner.fetch_market_data(ticker)
            if not market_data:
                logger.warning(f"[MarketRegistrar] Market {ticker} not found")
                return None

            market_info = self.state_tracker.parse_market_info(market_data)
            self.state_tracker.monitored_markets[ticker] = market_info

            self.notifier.log_market_registered(
                ticker, market_info.time_to_close_hours, market_info.state
            )

        except TRADING_ERRORS + (
            ValueError,
            KeyError,
        ):
            logger.exception(f"[MarketRegistrar] Failed to register market : ")
            return None
        else:
            return market_info
