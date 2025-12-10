"""Tests for CloseDetector helper."""

import pytest

from common.data_models.trading import OrderSide, PortfolioPosition
from common.market_lifecycle_monitor_helpers.close_detector import CloseDetector
from common.trading_exceptions import KalshiTradingError


class _StubTradingClient:
    def __init__(self, positions=None, error: Exception | None = None):
        self.positions = positions or []
        self.error = error
        self.calls = 0

    async def get_portfolio_positions(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.positions


class _StubEmergencyManager:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    async def emergency_close_position(self, position: PortfolioPosition, reason: str):
        self.calls.append((position.ticker, reason))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_get_market_positions_handles_trading_errors():
    detector = CloseDetector(_StubTradingClient(error=KalshiTradingError("fail")))
    positions = await detector.get_market_positions("TST")
    assert positions == []


@pytest.mark.asyncio
async def test_close_positions_requires_emergency_manager():
    detector = CloseDetector(_StubTradingClient())
    position = PortfolioPosition(
        ticker="TST", position_count=1, side=OrderSide.YES, average_price_cents=50
    )

    success, message = await detector.close_positions("TST", [position])

    assert not success
    assert "No emergency manager" in message


@pytest.mark.asyncio
async def test_close_positions_aggregates_results_and_errors():
    positions = [
        PortfolioPosition(
            ticker="TST", position_count=1, side=OrderSide.YES, average_price_cents=50
        ),
        PortfolioPosition(
            ticker="TST", position_count=1, side=OrderSide.NO, average_price_cents=50
        ),
    ]
    emergency_manager = _StubEmergencyManager(
        results=[
            (True, None, "closed first"),
            KalshiTradingError("boom"),
        ]
    )
    detector = CloseDetector(_StubTradingClient(), emergency_manager=emergency_manager)

    success, message = await detector.close_positions("TST", positions)

    assert not success
    assert "Error" in message
    assert emergency_manager.calls[0] == ("TST", "Market closure")


@pytest.mark.asyncio
async def test_handle_market_closure_short_circuits_on_errors(monkeypatch):
    detector = CloseDetector(_StubTradingClient())

    async def fail_positions(_ticker: str):
        raise ValueError("fail")

    monkeypatch.setattr(detector, "get_market_positions", fail_positions)

    success, message = await detector.handle_market_closure("ERR")

    assert not success
    assert "failed" in message


@pytest.mark.asyncio
async def test_handle_market_closure_returns_no_positions_message():
    detector = CloseDetector(_StubTradingClient(positions=[]))

    success, message = await detector.handle_market_closure("EMPTY")

    assert success
    assert message == "No positions to close"
