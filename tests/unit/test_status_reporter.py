from __future__ import annotations

from io import StringIO

import pytest

from common.status_reporter import StatusReporter


@pytest.fixture
def buffer_reporter():
    stream = StringIO()
    reporter = StatusReporter(output_stream=stream)
    return reporter, stream


def _lines(stream: StringIO):
    stream.seek(0)
    return stream.read().splitlines()


def test_tracking_and_market_status(buffer_reporter):
    reporter, stream = buffer_reporter

    reporter.tracking_started()
    reporter.markets_closed()
    reporter.markets_open()

    assert _lines(stream) == [
        "🔍 Tracking...",
        "🔒 Markets closed - waiting for next check",
        "✅ Markets open for trading",
    ]


def test_scanning_and_waiting(buffer_reporter):
    reporter, stream = buffer_reporter

    reporter.scanning_markets(42)
    reporter.waiting_for_next_scan(125)
    reporter.waiting_for_next_scan(45)

    assert _lines(stream) == [
        "🔍 Scanning 42 markets for opportunities...",
        "⏳ Waiting 2m 5s until next scan",
        "⏳ Waiting 45 seconds until next scan",
    ]


@pytest.mark.parametrize(
    "found,traded,closed,expected",
    [
        (0, 0, 0, ["📊 No trading opportunities found"]),
        (
            3,
            2,
            1,
            [
                "📊 Found 3 opportunities, 2 trades executed successfully, 1 opportunity could not be traded, and 1 market closed for the day"
            ],
        ),
        (1, 0, 0, ["📊 Found 1 opportunity, 1 opportunity could not be traded"]),
    ],
)
def test_opportunities_summary(found, traded, closed, expected, buffer_reporter):
    reporter, stream = buffer_reporter
    reporter.opportunities_summary(found, traded, closed)
    assert _lines(stream) == expected


def test_trade_opportunity_found_reports_details(buffer_reporter):
    reporter, stream = buffer_reporter
    reason = "Rule triggered (23)"
    reporter.trade_opportunity_found(
        ticker="TICKER",
        action="BUY",
        side="YES",
        price_cents=245,
        reason=reason,
        weather_context="Rain expected",
    )
    assert _lines(stream) == [
        "",
        "💰 Opportunity: BUY YES TICKER @ $2.45",
        "🌡️ Weather: Rain expected",
        f"📋 Rule: {reason}",
    ]


def test_trade_opportunity_interprets_yes_ask_rule(buffer_reporter):
    reporter, stream = buffer_reporter
    reason = "t_yes_ask comparison (40)"
    reporter.trade_opportunity_found(
        ticker="TICKER",
        action="SELL",
        side="YES",
        price_cents=380,
        reason=reason,
    )
    assert _lines(stream)[-1].startswith("📋 Rule: Theoretical YES ask (40")


def test_trade_updates(buffer_reporter):
    reporter, stream = buffer_reporter
    reporter.trade_executed("T", "BUY", "YES", 500, "order123")
    reporter.trade_failed("T", "insufficient liquidity")
    reporter.insufficient_balance("T", 1000, 200)
    reporter.balance_updated(5000, 6500)

    assert _lines(stream) == [
        "✅ Trade executed: BUY YES T @ $5.00 (Order: order123)",
        "❌ Trade failed for T: insufficient liquidity",
        "💸 Insufficient balance for T: need $10.00, have $2.00",
        "💰 Balance updated: $50.00 → $65.00 (+$15.00)",
    ]


def test_lifecycle_and_errors(buffer_reporter):
    reporter, stream = buffer_reporter
    reporter.initialization_complete()
    reporter.error_occurred("network down")
    reporter.shutdown_complete()
    reporter.checking_market_hours()

    assert _lines(stream) == [
        "🚀 Tracker initialized and ready",
        "❌ Error: network down",
        "🛑 Tracker shutdown complete",
        "🕐 Checking market hours...",
    ]
