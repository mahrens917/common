"""Stop-loss monitoring for positions."""

import asyncio
import logging
from typing import Dict

from ..kalshi_trading_client import KalshiTradingClient
from ..trading_exceptions import KalshiTradingError
from .position_closer import PositionCloser

logger = logging.getLogger(__name__)

TRADING_OPERATION_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
)


class StopLossMonitor:
    """Monitors positions for stop-loss triggers."""

    def __init__(self, trading_client: KalshiTradingClient, position_closer: PositionCloser):
        self.trading_client = trading_client
        self.position_closer = position_closer

    async def create_stop_loss_monitor(
        self,
        ticker: str,
        stop_loss_cents: int,
        monitored_positions: Dict,
        check_interval_seconds: float = 30.0,
    ):
        """
        Create a stop-loss monitor for a position.

        Args:
            ticker: Market ticker to monitor
            stop_loss_cents: Stop loss threshold (negative value)
            monitored_positions: Dict of currently monitored positions
            check_interval_seconds: How often to check position
        """
        logger.info(f"[StopLossMonitor] Starting stop-loss monitor for {ticker} at {stop_loss_cents}¢ loss")

        while ticker in monitored_positions:
            try:
                positions = await self.trading_client.get_portfolio_positions()
                position = next((p for p in positions if p.ticker == ticker), None)

                if not position:
                    logger.info(f"[StopLossMonitor] Position {ticker} no longer exists, stopping monitor")
                    break

                if position.unrealized_pnl_cents is not None and position.unrealized_pnl_cents <= stop_loss_cents:
                    logger.warning(
                        f"[StopLossMonitor] Stop-loss triggered for {ticker}: "
                        f"P&L={position.unrealized_pnl_cents}¢ <= {stop_loss_cents}¢"
                    )

                    await self.position_closer.emergency_close_position(position, "Stop-loss triggered")
                    break

                await asyncio.sleep(check_interval_seconds)

            except TRADING_OPERATION_ERRORS:
                logger.exception(f"[StopLossMonitor] Error in stop-loss monitor for : ")
                await asyncio.sleep(check_interval_seconds)

        logger.info(f"[StopLossMonitor] Stop-loss monitor for {ticker} ended")
