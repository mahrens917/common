"""Settlement checker for tracked markets."""

import asyncio
import logging
from typing import Dict

from ..trading_exceptions import KalshiTradingError
from .settlement_fetcher import SettlementFetcher
from .state_tracker import SettlementInfo, StateTracker

logger = logging.getLogger(__name__)

TRADING_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


class SettlementChecker:
    """Checks for market settlements."""

    def __init__(self, settlement_fetcher: SettlementFetcher, state_tracker: StateTracker):
        """
        Initialize settlement checker.

        Args:
            settlement_fetcher: Settlement fetcher for getting settlement data
            state_tracker: State tracker for caching settlements
        """
        self.settlement_fetcher = settlement_fetcher
        self.state_tracker = state_tracker

    async def check_settlements(self) -> Dict[str, SettlementInfo]:
        """
        Check for market settlements and calculate final P&L.

        Returns:
            Dict mapping ticker to settlement information
        """
        settlements = {}

        for ticker in self.state_tracker.monitored_markets.keys():
            try:
                settlement_info = await self.settlement_fetcher.fetch_settlement_info(ticker)
                if settlement_info and settlement_info.is_settled:
                    settlements[ticker] = settlement_info
                    self.state_tracker.settlement_cache[ticker] = settlement_info

                    logger.info(
                        f"[SettlementChecker] Market {ticker} settled: "
                        f"price={settlement_info.settlement_price_cents}¢, "
                        f"winner={settlement_info.winning_side}"
                    )

            except TRADING_ERRORS + (
                ValueError,
                KeyError,
            ):
                logger.exception(f"[SettlementChecker] Error checking settlement for : ")

        return settlements
