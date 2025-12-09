"""Handles market closure events."""

from typing import Any, Dict

from .close_detector import CloseDetector
from .state_tracker import MarketState


class ClosureHandler:
    """Processes closed markets and executes closure actions."""

    def __init__(self, close_detector: CloseDetector):
        self.close_detector = close_detector

    async def handle_closures(
        self, updated_markets: Dict[str, Any], results: Dict[str, Any]
    ) -> None:
        """Handle closed markets."""
        for ticker, market_info in updated_markets.items():
            if market_info.state == MarketState.CLOSED:
                results["closed_markets"].append(ticker)
                _success, message = await self.close_detector.handle_market_closure(ticker)
                results["actions_taken"].append(f"Closed {ticker}: {message}")
