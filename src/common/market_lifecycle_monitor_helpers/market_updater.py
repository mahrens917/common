"""Market state update handler."""

import logging
from typing import Any, Dict

from ..trading_exceptions import KalshiTradingError
from .state_tracker import StateTracker

logger = logging.getLogger(__name__)

TRADING_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    RuntimeError,
)


class MarketUpdater:
    """Handles market state updates."""

    def __init__(self, state_tracker: StateTracker):
        self.state_tracker = state_tracker

    async def update_all_markets(self) -> Dict[str, Any]:
        """Update all market states."""
        updated_markets = {}

        for ticker in list(self.state_tracker.monitored_markets.keys()):
            try:
                market_data = await self.state_tracker.scanner.fetch_market_data(ticker)
                if not market_data:
                    logger.warning(f"[MarketUpdater] Could not update market {ticker}")
                    continue

                previous_info = self.state_tracker.monitored_markets.get(ticker)
                market_info = self.state_tracker.parse_market_info(market_data)
                self.state_tracker.monitored_markets[ticker] = market_info
                updated_markets[ticker] = market_info

                if previous_info and market_info.state != previous_info.state:
                    logger.info(f"[MarketUpdater] State change for {ticker}: " f"{previous_info.state} -> {market_info.state}")

            except TRADING_ERRORS + (
                ValueError,
                KeyError,
            ):
                logger.exception(f"[MarketUpdater] Error updating market : ")

        return updated_markets
