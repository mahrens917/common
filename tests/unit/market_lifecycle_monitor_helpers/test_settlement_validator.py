"""Tests for SettlementValidator."""

from types import SimpleNamespace

import pytest

from common.data_models.trading import OrderSide, PortfolioPosition
from common.market_lifecycle_monitor_helpers.settlement_validator import SettlementValidator
from common.market_lifecycle_monitor_helpers.state_tracker import SettlementInfo


@pytest.mark.asyncio
async def test_validate_settlement_pnl_handles_unsettled_market():
    validator = SettlementValidator(SimpleNamespace(settlement_cache={}))
    position = PortfolioPosition(ticker="TST", position_count=1, average_price_cents=10)

    valid, message, pnl = await validator.validate_settlement_pnl("TST", position)

    assert not valid
    assert message == "Market not settled"
    assert pnl is None


@pytest.mark.asyncio
async def test_validate_settlement_pnl_requires_price():
    settlement_info = SettlementInfo(
        ticker="TST",
        settlement_price_cents=None,
        settlement_time=None,
        winning_side=None,
        is_settled=True,
    )
    validator = SettlementValidator(SimpleNamespace(settlement_cache={"TST": settlement_info}))
    position = PortfolioPosition(ticker="TST", position_count=1, average_price_cents=10)

    valid, message, pnl = await validator.validate_settlement_pnl("TST", position)

    assert not valid
    assert message == "No settlement price available"
    assert pnl is None


@pytest.mark.asyncio
async def test_validate_settlement_pnl_computes_expected_value():
    settlement_info = SettlementInfo(
        ticker="TST",
        settlement_price_cents=70,
        settlement_time=None,
        winning_side="yes",
        is_settled=True,
    )
    validator = SettlementValidator(SimpleNamespace(settlement_cache={"TST": settlement_info}))
    position = PortfolioPosition(
        ticker="TST",
        position_count=2,
        average_price_cents=20,
        side=OrderSide.NO,
    )

    valid, message, pnl = await validator.validate_settlement_pnl("TST", position)

    assert valid
    assert message == "Settlement P&L calculated"
    assert pnl == (100 - 70) * 2 - 20 * 2


@pytest.mark.asyncio
async def test_validate_settlement_pnl_returns_error_on_attribute_failure():
    validator = SettlementValidator(SimpleNamespace())
    position = PortfolioPosition(ticker="TST", position_count=1, average_price_cents=10)

    valid, message, pnl = await validator.validate_settlement_pnl("TST", position)

    assert not valid
    assert message == "P&L validation error"
    assert pnl is None
