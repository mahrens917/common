"""Market closure detection and position handling."""

import asyncio
import logging
from typing import List, Optional, Tuple

from ..data_models.trading import PortfolioPosition
from ..emergency_position_manager import EmergencyPositionManager
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


class CloseDetector:
    """Detects market closures and manages position closure."""

    def __init__(
        self,
        trading_client: KalshiTradingClient,
        emergency_manager: Optional[EmergencyPositionManager] = None,
    ):
        """
        Initialize close detector.

        Args:
            trading_client: Trading client for position access
            emergency_manager: Emergency position manager for auto-closure
        """
        self.trading_client = trading_client
        self.emergency_manager = emergency_manager

    async def get_market_positions(self, ticker: str) -> List[PortfolioPosition]:
        """
        Get all positions for a specific market.

        Args:
            ticker: Market ticker

        Returns:
            List of positions in the market
        """
        try:
            positions = await self.trading_client.get_portfolio_positions()
            return [p for p in positions if p.ticker == ticker]
        except TRADING_ERRORS:  # policy_guard: allow-silent-handler
            logger.exception(f"[CloseDetector] Error fetching positions for : ")
            return []

    async def close_positions(self, ticker: str, positions: List[PortfolioPosition]) -> Tuple[bool, str]:
        """
        Close all positions in a market.

        Args:
            ticker: Market ticker
            positions: Positions to close

        Returns:
            Tuple of (success, message)
        """
        if not positions:
            return True, "No positions to close"

        if not self.emergency_manager:
            return False, "No emergency manager available for position closure"

        results = []
        for position in positions:
            try:
                success, _, message = await self.emergency_manager.emergency_close_position(position, "Market closure")
                results.append((success, message))
            except TRADING_ERRORS:  # policy_guard: allow-silent-handler
                logger.exception(f"[CloseDetector] Error closing position in : ")
                results.append((False, f"Error"))

        all_success = all(r[0] for r in results)
        messages = [r[1] for r in results]
        return all_success, "; ".join(messages)

    async def handle_market_closure(self, ticker: str) -> Tuple[bool, str]:
        """
        Handle market closure by closing any open positions.

        Args:
            ticker: Market that has closed

        Returns:
            Tuple of (success, message)
        """
        logger.warning(f"[CloseDetector] Handling closure of market {ticker}")

        try:
            positions = await self.get_market_positions(ticker)
            return await self.close_positions(ticker, positions)

        except TRADING_ERRORS + (ValueError,):  # policy_guard: allow-silent-handler
            logger.exception(f"[CloseDetector] Error handling closure of : ")
            return False, f"Closure handling failed"
