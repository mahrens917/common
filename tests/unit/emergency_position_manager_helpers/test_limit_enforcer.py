from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.emergency_position_manager_helpers.limit_enforcer import (
    LimitEnforcer,
    _calculate_total_exposure,
    _sorted_high_risk_assessments,
)


class DummyRiskAssessment:
    def __init__(self, ticker, requires_closure, score):
        self.ticker = ticker
        self.requires_closure = requires_closure
        self.risk_score = score


def make_position(ticker, value):
    return SimpleNamespace(ticker=ticker, market_value_cents=value, last_updated=0)


@pytest.mark.asyncio
async def test_monitor_and_enforce_limits_closes_high_risk_positions():
    trading_client = MagicMock()
    pos_high = make_position("a", 200)
    trading_client.get_portfolio_positions = AsyncMock(return_value=[pos_high])
    risk_assessor = MagicMock()
    risk_assessor.assess_position_risk = AsyncMock(return_value=DummyRiskAssessment("a", True, 5.0))
    position_closer = MagicMock()
    position_closer.emergency_close_position = AsyncMock()
    risk_limits = SimpleNamespace(max_total_exposure_cents=50)

    enforcer = LimitEnforcer(trading_client, risk_assessor, position_closer, risk_limits)

    assessments = await enforcer.monitor_and_enforce_limits({"a": 0})

    assert assessments and assessments[0].requires_closure is True
    position_closer.emergency_close_position.assert_awaited()


@pytest.mark.asyncio
async def test_monitor_and_enforce_limits_handles_errors_gracefully(caplog):
    trading_client = MagicMock()
    trading_client.get_portfolio_positions = AsyncMock(side_effect=RuntimeError("boom"))
    risk_assessor = MagicMock()
    position_closer = MagicMock()
    risk_limits = SimpleNamespace(max_total_exposure_cents=50)

    enforcer = LimitEnforcer(trading_client, risk_assessor, position_closer, risk_limits)
    caplog.set_level("ERROR")

    assessments = await enforcer.monitor_and_enforce_limits({"a": 0})

    assert assessments == []
    assert "Error monitoring positions" in caplog.text


def test_calculate_total_exposure_filters_monitored():
    positions = [make_position("a", 100), make_position("b", -50)]
    total = _calculate_total_exposure(positions, {"a": 0})
    assert total == 100


def test_sorted_high_risk_assessments_orders_descending():
    assessments = [
        DummyRiskAssessment("a", True, 1.0),
        DummyRiskAssessment("b", True, 3.0),
        DummyRiskAssessment("c", False, 2.0),
    ]
    sorted_assessments = _sorted_high_risk_assessments(assessments)
    assert [a.ticker for a in sorted_assessments] == ["b", "a"]
