"""Tests for ClosureHandler."""

import pytest

from src.common.market_lifecycle_monitor_helpers.close_detector import CloseDetector
from src.common.market_lifecycle_monitor_helpers.closure_handler import ClosureHandler
from src.common.market_lifecycle_monitor_helpers.state_tracker import MarketState


class _StubCloseDetector(CloseDetector):
    def __init__(self):
        super().__init__(trading_client=None, emergency_manager=None)
        self.calls = []

    async def handle_market_closure(self, ticker: str):
        self.calls.append(ticker)
        return True, f"closed {ticker}"


@pytest.mark.asyncio
async def test_handle_closures_processes_only_closed_markets():
    close_detector = _StubCloseDetector()
    handler = ClosureHandler(close_detector)
    updated_markets = {
        "OPEN": type("Market", (), {"state": MarketState.ACTIVE}),
        "CLOSED": type("Market", (), {"state": MarketState.CLOSED}),
    }
    results = {"closed_markets": [], "actions_taken": []}

    await handler.handle_closures(updated_markets, results)

    assert results["closed_markets"] == ["CLOSED"]
    assert "Closed CLOSED: closed CLOSED" in results["actions_taken"][0]
    assert close_detector.calls == ["CLOSED"]
