from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.common.data_models.trading import OrderSide, PortfolioPosition
from src.common.market_lifecycle_monitor import (
    MarketInfo,
    MarketLifecycleMonitor,
    SettlementInfo,
)
from src.common.market_lifecycle_monitor_helpers.state_tracker import MarketState


class FakeTradingClient:
    def __init__(self):
        self.positions = []
        self.kalshi_client = AsyncMock()
        self.kalshi_client.api_request = AsyncMock()

    async def get_portfolio_positions(self):
        return list(self.positions)


class FakeEmergencyManager:
    def __init__(self, succeed=True):
        self.succeed = succeed
        self.calls = []

    async def emergency_close_position(self, position, reason):
        self.calls.append((position, reason))
        return self.succeed, None, "closed" if self.succeed else "failed"


@pytest.fixture
def fixed_now(monkeypatch):
    now = datetime(2024, 8, 20, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "src.common.market_lifecycle_monitor.get_current_utc",
        lambda: now,
    )
    return now


def make_market(close_delta_hours, status="active"):
    close_time = datetime(2024, 8, 20, 12, tzinfo=timezone.utc) + timedelta(hours=close_delta_hours)
    return {
        "ticker": "KX-TEST",
        "title": "Test Market",
        "close_time": close_time.isoformat().replace("+00:00", "Z"),
        "status": status,
    }


@pytest.mark.asyncio
async def test_register_market_success(monkeypatch, fixed_now):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client, closure_warning_hours=3.0)
    monkeypatch.setattr(monitor, "_fetch_market_data", AsyncMock(return_value=make_market(2)))

    info = await monitor.register_market("KX-TEST")
    assert isinstance(info, MarketInfo)
    assert info.state == MarketState.CLOSING_SOON
    assert monitor.monitored_markets["KX-TEST"].ticker == "KX-TEST"


@pytest.mark.asyncio
async def test_register_market_not_found(monkeypatch):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)
    monkeypatch.setattr(monitor, "_fetch_market_data", AsyncMock(return_value=None))
    assert await monitor.register_market("MISSING") is None


@pytest.mark.asyncio
async def test_update_market_states(monkeypatch, fixed_now):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)
    monitor.monitored_markets["KX-TEST"] = MarketInfo(
        ticker="KX-TEST",
        title="Old",
        close_time=fixed_now + timedelta(hours=5),
        status="active",
        state=MarketState.ACTIVE,
        time_to_close_hours=5.0,
    )

    monkeypatch.setattr(
        monitor,
        "_fetch_market_data",
        AsyncMock(return_value=make_market(-1, status="closed")),
    )
    updated = await monitor.update_market_states()
    assert updated["KX-TEST"].state == MarketState.CLOSED


@pytest.mark.asyncio
async def test_check_closure_warnings():
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)
    monitor.monitored_markets = {
        "closing": MarketInfo(
            ticker="closing",
            title="",
            close_time=datetime.now(timezone.utc),
            status="active",
            state=MarketState.CLOSING_SOON,
            time_to_close_hours=1.0,
        ),
        "active": MarketInfo(
            ticker="active",
            title="",
            close_time=datetime.now(timezone.utc),
            status="active",
            state=MarketState.ACTIVE,
            time_to_close_hours=5.0,
        ),
    }

    closing = await monitor.check_closure_warnings()
    assert [m.ticker for m in closing] == ["closing"]


@pytest.mark.asyncio
async def test_handle_market_closure_with_emergency(monkeypatch):
    client = FakeTradingClient()
    emergency = FakeEmergencyManager()
    monitor = MarketLifecycleMonitor(client, emergency)

    position = PortfolioPosition(
        ticker="KX-TEST",
        position_count=1,
        side=OrderSide.YES,
        market_value_cents=50,
        unrealized_pnl_cents=10,
        average_price_cents=40,
        last_updated=datetime.now(timezone.utc),
    )
    client.positions = [position]

    success, message = await monitor.handle_market_closure("KX-TEST")
    assert success is True
    assert "closed" in message
    assert emergency.calls


@pytest.mark.asyncio
async def test_handle_market_closure_without_emergency(monkeypatch):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client, emergency_manager=None)
    client.positions = [
        PortfolioPosition(
            ticker="KX-TEST",
            position_count=1,
            side=OrderSide.NO,
            market_value_cents=50,
            unrealized_pnl_cents=10,
            average_price_cents=40,
            last_updated=datetime.now(timezone.utc),
        )
    ]

    success, message = await monitor.handle_market_closure("KX-TEST")
    assert success is False
    assert "No emergency manager" in message


@pytest.mark.asyncio
async def test_check_settlements(monkeypatch):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)
    monitor.monitored_markets["KX-TEST"] = MarketInfo(
        ticker="KX-TEST",
        title="",
        close_time=datetime.now(timezone.utc),
        status="settled",
        state=MarketState.SETTLED,
        time_to_close_hours=0.0,
    )

    settlement = SettlementInfo(
        ticker="KX-TEST",
        settlement_price_cents=55,
        settlement_time=datetime.now(timezone.utc),
        winning_side="YES",
        is_settled=True,
    )
    monkeypatch.setattr(monitor, "_fetch_settlement_info", AsyncMock(return_value=settlement))

    results = await monitor.check_settlements()
    assert results["KX-TEST"].winning_side == "YES"
    assert monitor.settlement_cache["KX-TEST"].is_settled is True


@pytest.mark.asyncio
async def test_validate_settlement_pnl(monkeypatch, fixed_now):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)
    monitor.settlement_cache["KX-TEST"] = SettlementInfo(
        ticker="KX-TEST",
        settlement_price_cents=60,
        settlement_time=None,
        winning_side="YES",
        is_settled=True,
    )
    position = PortfolioPosition(
        ticker="KX-TEST",
        position_count=2,
        side=OrderSide.YES,
        market_value_cents=80,
        unrealized_pnl_cents=0,
        average_price_cents=40,
        last_updated=fixed_now,
    )

    ok, msg, pnl = await monitor.validate_settlement_pnl("KX-TEST", position)
    assert ok is True
    assert pnl == (60 * 2) - (40 * 2)


@pytest.mark.asyncio
async def test_monitor_lifecycle_events(monkeypatch):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)

    # Set up monitored markets with a CLOSING_SOON market
    monitor.state_tracker.monitored_markets["KX-SOON"] = MarketInfo(
        ticker="KX-SOON",
        title="",
        close_time=datetime.now(timezone.utc),
        status="open",
        state=MarketState.CLOSING_SOON,
        time_to_close_hours=1.5,
    )

    # Monkeypatch orchestrator components
    monkeypatch.setattr(
        monitor.orchestrator.market_updater,
        "update_all_markets",
        AsyncMock(
            return_value={
                "KX": MarketInfo(
                    ticker="KX",
                    title="",
                    close_time=datetime.now(timezone.utc),
                    status="closed",
                    state=MarketState.CLOSED,
                    time_to_close_hours=0.0,
                )
            }
        ),
    )
    monkeypatch.setattr(
        monitor.orchestrator.closure_handler,
        "handle_closures",
        AsyncMock(
            side_effect=lambda markets, results: results["actions_taken"].append("Closed KX")
        ),
    )
    monkeypatch.setattr(
        monitor.orchestrator.settlement_checker,
        "check_settlements",
        AsyncMock(return_value={"KX": "settled"}),
    )

    results = await monitor.monitor_lifecycle_events()
    assert len(results["closing_soon"]) == 1
    assert results["closing_soon"][0].ticker == "KX-SOON"
    assert "Closed KX" in results["actions_taken"][0]
    assert results["settlements"] == {"KX": "settled"}


@pytest.mark.asyncio
async def test_fetch_market_data_success(monkeypatch):
    client = FakeTradingClient()
    payload = {"market": {"ticker": "KX"}}
    client.kalshi_client.api_request.return_value = payload
    monitor = MarketLifecycleMonitor(client)

    data = await monitor._fetch_market_data("KX")
    assert data == {"ticker": "KX"}
    client.kalshi_client.api_request.assert_awaited()


@pytest.mark.asyncio
async def test_fetch_market_data_failure(monkeypatch):
    client = FakeTradingClient()
    client.kalshi_client.api_request.side_effect = RuntimeError("boom")
    monitor = MarketLifecycleMonitor(client)
    assert await monitor._fetch_market_data("KX") is None


@pytest.mark.asyncio
async def test_fetch_settlement_info_returns_winner(monkeypatch, fixed_now):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)
    monkeypatch.setattr(
        monitor.scanner,
        "fetch_market_data",
        AsyncMock(return_value={"ticker": "KX", "status": "settled", "result_price": 30}),
    )
    info = await monitor._fetch_settlement_info("KX")
    assert info.winning_side == "NO"


def test_parse_market_info_handles_invalid_close(monkeypatch):
    client = FakeTradingClient()
    monitor = MarketLifecycleMonitor(client)
    monkeypatch.setattr(
        "src.common.market_lifecycle_monitor.get_current_utc",
        lambda: datetime(2024, 8, 20, tzinfo=timezone.utc),
    )

    market_data = {"ticker": "KX", "title": "", "close_time": "invalid", "status": "active"}
    info = monitor._parse_market_info(market_data)
    assert info.state in {MarketState.ACTIVE, MarketState.UNKNOWN}
