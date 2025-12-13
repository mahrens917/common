"""Orchestrates lifecycle event monitoring."""

import asyncio
import logging
from typing import Any, Dict

from ..trading_exceptions import KalshiTradingError
from .close_detector import CloseDetector
from .closure_handler import ClosureHandler
from .market_updater import MarketUpdater
from .notification_sender import NotificationSender
from .settlement_checker import SettlementChecker
from .state_tracker import MarketInfo, MarketState, StateTracker

logger = logging.getLogger(__name__)

TRADING_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


class LifecycleOrchestrator:
    """Orchestrates lifecycle event checks and responses."""

    def __init__(
        self,
        state_tracker: StateTracker,
        close_detector: CloseDetector,
        notifier: NotificationSender,
        settlement_checker: SettlementChecker,
    ):
        self.state_tracker = state_tracker
        self.notifier = notifier
        self.settlement_checker = settlement_checker
        self.market_updater = MarketUpdater(state_tracker)
        self.closure_handler = ClosureHandler(close_detector)

    async def monitor_lifecycle_events(self) -> Dict[str, Any]:
        """Monitor all lifecycle events for registered markets."""
        results = {
            "updated_markets": {},
            "closing_soon": [],
            "closed_markets": [],
            "settlements": {},
            "actions_taken": [],
        }

        try:
            results["updated_markets"] = await self.market_updater.update_all_markets()
            results["closing_soon"] = self.get_closing_soon_markets()
            self.notifier.send_closure_warnings(results["closing_soon"])
            await self.closure_handler.handle_closures(results["updated_markets"], results)
            results["settlements"] = await self.settlement_checker.check_settlements()
        except TRADING_ERRORS + (  # policy_guard: allow-silent-handler
            ValueError,
            TypeError,
        ) as e:
            logger.exception("[LifecycleOrchestrator] Error in lifecycle monitoring: ")
            results["error"] = str(e)

        return results

    def get_closing_soon_markets(self) -> list[MarketInfo]:
        """Return the markets that are closing soon."""
        return self._collect_closing_soon_markets()

    def _collect_closing_soon_markets(self) -> list[MarketInfo]:
        """Get markets that are closing soon."""
        return [m for m in self.state_tracker.monitored_markets.values() if m.state == MarketState.CLOSING_SOON]
