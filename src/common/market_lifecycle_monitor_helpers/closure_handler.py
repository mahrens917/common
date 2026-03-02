"""Handles market closure events."""

import asyncio
from typing import Any, Dict, List, Tuple

from .close_detector import CloseDetector
from .state_tracker import MarketState


class ClosureHandler:
    """Processes closed markets and executes closure actions."""

    def __init__(self, close_detector: CloseDetector):
        self.close_detector = close_detector

    async def handle_closures(self, updated_markets: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Handle closed markets."""
        closed: List[Tuple[str, Any]] = [
            (ticker, market_info) for ticker, market_info in updated_markets.items() if market_info.state == MarketState.CLOSED
        ]
        if not closed:
            return
        outcomes = await asyncio.gather(
            *(self.close_detector.handle_market_closure(ticker) for ticker, _ in closed),
            return_exceptions=True,
        )
        for (ticker, _), outcome in zip(closed, outcomes):
            if isinstance(outcome, BaseException):
                raise outcome
            _success, message = outcome
            results["closed_markets"].append(ticker)
            results["actions_taken"].append(f"Closed {ticker}: {message}")
