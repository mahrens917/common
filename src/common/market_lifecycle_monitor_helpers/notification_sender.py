"""Notification sender for lifecycle events."""

import logging
from typing import List

from .state_tracker import MarketInfo, MarketState

logger = logging.getLogger(__name__)


class NotificationSender:
    """Sends notifications for market lifecycle events."""

    def send_closure_warnings(self, markets: List[MarketInfo]) -> None:
        """
        Send warnings for markets closing soon.

        Args:
            markets: List of markets closing soon
        """
        for market_info in markets:
            logger.warning(f"[NotificationSender] Market {market_info.ticker} " f"closing in {market_info.time_to_close_hours:.1f}h")

    def log_state_change(self, ticker: str, previous_state: MarketState, new_state: MarketState) -> None:
        """
        Log market state change.

        Args:
            ticker: Market ticker
            previous_state: Previous state
            new_state: New state
        """
        logger.info(f"[NotificationSender] Market {ticker} state changed: " f"{previous_state.value} -> {new_state.value}")

    def log_market_registered(self, ticker: str, time_to_close_hours: float, state: MarketState) -> None:
        """
        Log market registration.

        Args:
            ticker: Market ticker
            time_to_close_hours: Hours until close
            state: Current market state
        """
        logger.info(f"[NotificationSender] Registered market {ticker}: " f"closes in {time_to_close_hours:.1f}h, state={state.value}")
