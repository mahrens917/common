"""Tests for the report generator coordinator."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from common import report_generator as report_module
from common.exceptions import ConfigurationError
from common.report_generator import ReportGenerator


class DummyMessageFormatter:
    def format_error_message(self, msg):
        return f"error:{msg}"

    def format_no_data_message(self, date_range):
        return f"no-data:{date_range}"


class DummyDelegator:
    def __init__(self, *_args, **_kwargs):
        self.generate_daily_report = AsyncMock(return_value="daily")
        self.generate_historical_report = AsyncMock(return_value="history")
        self.generate_current_day_report = AsyncMock(return_value="current")
        self.generate_settlement_notification = AsyncMock(return_value="settlement")
        self.generate_summary_stats = AsyncMock(return_value="summary")
        self.generate_unified_pnl_report = AsyncMock(return_value="unified")
        self.generate_unified_pnl_data = AsyncMock(return_value={"data": 1})


@pytest.fixture(autouse=True)
def stub_coordinators(monkeypatch):
    def fake_create_coordinators(pnl_calculator, timezone):
        return (
            DummyMessageFormatter(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

    monkeypatch.setattr(
        report_module, "CoordinatorFactory", MagicMock(create_coordinators=fake_create_coordinators)
    )
    monkeypatch.setattr(report_module, "ReportDelegator", DummyDelegator)
    monkeypatch.setattr(report_module, "load_configured_timezone", lambda: "UTC")
    yield


@pytest.mark.asyncio
async def test_report_generator_delegates(monkeypatch):
    generator = ReportGenerator(MagicMock())

    assert await generator.generate_daily_report(date(2023, 1, 1)) == "daily"
    assert (
        await generator.generate_historical_report(date(2023, 1, 1), date(2023, 1, 2)) == "history"
    )
    assert await generator.generate_current_day_report() == "current"
    assert (
        await generator.generate_settlement_notification(date(2023, 1, 1), ["settled"])
        == "settlement"
    )
    assert await generator.generate_summary_stats(7) == "summary"
    assert await generator.generate_unified_pnl_report() == "unified"
    assert await generator.generate_unified_pnl_data() == {"data": 1}
    assert generator.format_error_message("oops") == "error:oops"
    assert generator.format_no_data_message("2023-01") == "no-data:2023-01"


def test_report_generator_timezone_failure(monkeypatch):
    def _raise():
        raise RuntimeError("fail")

    monkeypatch.setattr(report_module, "load_configured_timezone", _raise)
    monkeypatch.setattr(
        report_module,
        "CoordinatorFactory",
        MagicMock(
            create_coordinators=lambda *_: (
                DummyMessageFormatter(),
                MagicMock(),
                MagicMock(),
                MagicMock(),
            )
        ),
    )
    monkeypatch.setattr(report_module, "ReportDelegator", DummyDelegator)

    with pytest.raises(ConfigurationError, match="Failed to load reporting timezone configuration"):
        ReportGenerator(MagicMock())
