from datetime import date, datetime, timedelta, timezone
from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from common.data_models.trade_record import TradeRecord, TradeSide
from common.pnl_calculator import PnLCalculator

_CONST_24 = 24
_CONST_250 = 250
_CONST_42 = 42
_TEST_COUNT_2 = 2
_TEST_ID_123 = 123


@pytest.fixture(autouse=True)
def _patch_timezone(monkeypatch):
    monkeypatch.setattr("common.pnl_calculator.load_configured_timezone", lambda: "UTC")


def _build_trade(
    order_id: str = "OID",
    station: str = "DEN",
    rule: str = "rule_3",
    pnl_offset: int = 200,
    settled: bool = False,
):
    trade = TradeRecord(
        order_id=order_id,
        market_ticker="KXHIGHNYC-25JAN01",
        trade_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        trade_side=TradeSide.YES,
        quantity=1,
        price_cents=50,
        fee_cents=5,
        cost_cents=55,
        market_category="weather",
        weather_station=station,
        trade_rule=rule,
        trade_reason="Test reason",
        last_yes_bid=(55 + pnl_offset) / 1,  # derive pnl via bid price
    )
    if settled:
        trade.settlement_price_cents = 80
        trade.settlement_time = datetime(2024, 1, 2, tzinfo=timezone.utc)
    return trade


class FakeTradeStore:
    def __init__(self):
        self.summary_payloads = {}
        self.trades_by_range = []
        self.closed_today_trades = []
        self.closed_yesterday_trades = []
        self.unrealized_trades = {}
        self.raise_on = {}

    async def get_trades_by_date_range(self, start_date, end_date):
        if exc := self.raise_on.get("get_trades_by_date_range"):
            raise exc

        data = self.trades_by_range
        if isinstance(data, dict):
            return list(data.get((start_date, end_date), []))
        return list(data)

    async def get_daily_summary(self, trade_date):
        if exc := self.raise_on.get("get_daily_summary"):
            raise exc
        return self.summary_payloads.get(trade_date)

    async def store_daily_summary(self, report):
        if exc := self.raise_on.get("store_daily_summary"):
            raise exc
        self.summary_payloads[report.start_date] = {
            "date": report.start_date.isoformat(),
            "total_trades": report.total_trades,
            "total_cost_cents": report.total_cost_cents,
            "total_pnl_cents": report.total_pnl_cents,
            "win_rate": report.win_rate,
        }

    async def store_unrealized_pnl_data(self, key, payload):
        if exc := self.raise_on.get("store_unrealized_pnl_data"):
            raise exc
        self.summary_payloads[("unrealized", key)] = payload

    async def get_unrealized_pnl_data(self, key):
        if exc := self.raise_on.get("get_unrealized_pnl_data"):
            raise exc
        return self.summary_payloads.get(("unrealized", key))

    async def get_trades_closed_today(self):
        if exc := self.raise_on.get("get_trades_closed_today"):
            raise exc
        return list(self.closed_today_trades)

    async def get_trades_closed_yesterday(self):
        if exc := self.raise_on.get("get_trades_closed_yesterday"):
            raise exc
        return list(self.closed_yesterday_trades)

    async def get_unrealized_trades_for_date(self, target_date):
        if exc := self.raise_on.get("get_unrealized_trades_for_date"):
            raise exc
        return list(self.unrealized_trades.get(target_date, []))


@pytest.mark.asyncio
async def test_calculate_unrealized_pnl_sums_current_pnl():
    trades = [_build_trade(pnl_offset=5), _build_trade(order_id="OID2", pnl_offset=-3)]
    store = FakeTradeStore()
    calculator = PnLCalculator(store)

    total = await calculator.calculate_unrealized_pnl(trades)
    assert total == sum(t.calculate_current_pnl_cents() for t in trades)


def test_standardize_station_name_handles_mappings():
    from common.pnl_calculator_helpers.station_normalizer import StationNameNormalizer

    normalizer = StationNameNormalizer()

    assert normalizer.standardize_station_name("DEN") == "KDEN"
    assert normalizer.standardize_station_name("AUS") == "KAUS"
    assert normalizer.standardize_station_name("KPHX") == "KPHX"
    assert normalizer.standardize_station_name("NY") == "KNYC"
    assert normalizer.standardize_station_name("ABC") == "KABC"
    assert normalizer.standardize_station_name("LONGER") == "LONGER"


@pytest.mark.asyncio
async def test_station_breakdown_consolidates_and_counts():
    from common.pnl_calculator_helpers.breakdown_calculator import BreakdownCalculator

    trades = [
        _build_trade(station="DEN", pnl_offset=5),
        _build_trade(order_id="OID2", station="KDEN", pnl_offset=-2),
    ]
    breakdown_calc = BreakdownCalculator()

    breakdown = await breakdown_calc.calculate_station_breakdown(trades)

    assert set(breakdown.keys()) == {"KDEN"}
    den = breakdown["KDEN"]
    assert den.trades_count == _TEST_COUNT_2
    assert den.cost_cents == sum(t.cost_cents for t in trades)
    assert den.pnl_cents == sum(t.calculate_current_pnl_cents() for t in trades)
    assert 0.0 <= den.win_rate <= 1.0


@pytest.mark.asyncio
async def test_rule_breakdown_groups_by_rule():
    from common.pnl_calculator_helpers.breakdown_calculator import BreakdownCalculator

    trades = [
        _build_trade(rule="rule_3", pnl_offset=5),
        _build_trade(order_id="OID2", rule="rule_4", pnl_offset=-10),
    ]
    breakdown_calc = BreakdownCalculator()

    breakdown = await breakdown_calc.calculate_rule_breakdown(trades)

    assert set(breakdown.keys()) == {"rule_3", "rule_4"}
    assert breakdown["rule_3"].trades_count == 1
    assert breakdown["rule_4"].trades_count == 1


@pytest.mark.asyncio
async def test_generate_aggregated_report_returns_empty_when_no_trades():
    store = FakeTradeStore()
    calculator = PnLCalculator(store)

    report = await calculator.generate_aggregated_report(date(2024, 1, 1), date(2024, 1, 1))

    assert report.total_trades == 0
    assert report.total_pnl_cents == 0
    assert report.by_weather_station == {}


@pytest.mark.asyncio
async def test_calculate_daily_summary_uses_cache():
    trade_day = date(2024, 1, 2)
    store = FakeTradeStore()
    cached = {
        "date": trade_day.isoformat(),
        "total_trades": 5,
        "total_cost_cents": 1000,
        "total_pnl_cents": 150,
        "win_rate": 0.4,
    }
    store.summary_payloads[trade_day] = cached

    calculator = PnLCalculator(store)
    summary = await calculator.calculate_daily_summary(trade_day)
    assert summary == cached


@pytest.mark.asyncio
async def test_store_unrealized_pnl_snapshot_persists(monkeypatch):
    store = FakeTradeStore()
    calculator = PnLCalculator(store)

    fixed_now = datetime(2024, 1, 5, tzinfo=timezone.utc)
    monkeypatch.setattr("common.pnl_calculator_helpers.snapshot_manager.get_current_utc", lambda: fixed_now)

    await calculator.store_unrealized_pnl_snapshot(date(2024, 1, 4), 250)

    payload = store.summary_payloads[("unrealized", "pnl:unrealized:2024-01-04")]
    assert payload["unrealized_pnl_cents"] == _CONST_250
    assert payload["timestamp"] == fixed_now.isoformat()


@pytest.mark.asyncio
async def test_get_unrealized_pnl_snapshot_reads_from_store():
    store = FakeTradeStore()
    key = "pnl:unrealized:2024-01-03"
    store.summary_payloads[("unrealized", key)] = {"unrealized_pnl_cents": 123}
    calculator = PnLCalculator(store)

    value = await calculator.get_unrealized_pnl_snapshot(date(2024, 1, 3))
    assert value == _TEST_ID_123


@pytest.mark.asyncio
async def test_get_unrealized_pnl_snapshot_handles_error():
    store = FakeTradeStore()
    store.raise_on["get_unrealized_pnl_data"] = RuntimeError("snapshot error")
    calculator = PnLCalculator(store)

    value = await calculator.get_unrealized_pnl_snapshot(date(2024, 1, 4))
    assert value is None


@pytest.mark.asyncio
async def test_update_daily_unrealized_pnl_persists(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade()
    store.trades_by_range = [trade]
    calculator = PnLCalculator(store)

    monkeypatch.setattr("common.pnl_calculator.PnLCalculator.store_unrealized_pnl_snapshot", AsyncMock())

    result = await calculator.update_daily_unrealized_pnl(date(2024, 1, 1))
    assert result == trade.calculate_current_pnl_cents()


@pytest.mark.asyncio
async def test_generate_aggregated_report_with_trades(monkeypatch):
    store = FakeTradeStore()
    trades = [
        _build_trade(pnl_offset=10),
        _build_trade(order_id="OID2", pnl_offset=-5, station="CHI", rule="rule_4"),
    ]
    store.trades_by_range = trades
    calculator = PnLCalculator(store)

    start = date(2024, 1, 1)
    end = date(2024, 1, 2)
    report = await calculator.generate_aggregated_report(start, end)

    expected_pnl = sum(t.calculate_current_pnl_cents() for t in trades)
    assert report.total_trades == _TEST_COUNT_2
    assert report.total_cost_cents == sum(t.cost_cents for t in trades)
    assert report.total_pnl_cents == expected_pnl
    assert report.win_rate > 0
    assert set(report.by_rule.keys()) == {"rule_3", "rule_4"}
    assert "KCHI" in report.by_weather_station


@pytest.mark.asyncio
async def test_generate_aggregated_report_raises_on_trade_failure():
    store = FakeTradeStore()
    trade = _build_trade()

    def _blow_up(self):
        raise RuntimeError("pnl failure")

    trade.calculate_current_pnl_cents = MethodType(_blow_up, trade)
    store.trades_by_range = [trade]
    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="pnl failure"):
        await calculator.generate_aggregated_report(date(2024, 1, 1), date(2024, 1, 1))


@pytest.mark.asyncio
async def test_calculate_daily_summary_generates_and_caches(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade()
    store.trades_by_range = [trade]
    calculator = PnLCalculator(store)

    target_day = date(2024, 1, 3)
    summary = await calculator.calculate_daily_summary(target_day)

    assert summary["total_trades"] == 1
    assert summary["total_pnl_cents"] == trade.calculate_current_pnl_cents()
    assert store.summary_payloads[target_day]["total_trades"] == 1


@pytest.mark.asyncio
async def test_calculate_daily_summary_returns_none_on_error():
    store = FakeTradeStore()
    store.raise_on["get_trades_by_date_range"] = RuntimeError("db down")

    calculator = PnLCalculator(store)
    result = await calculator.calculate_daily_summary(date(2024, 1, 4))
    assert result is None


@pytest.mark.asyncio
async def test_get_current_day_unrealized_pnl(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade(pnl_offset=5)
    today = date(2024, 1, 5)
    store.trades_by_range = {(today, today): [trade]}
    calculator = PnLCalculator(store)

    monkeypatch.setattr(
        "common.pnl_calculator_helpers.daily_operations.get_timezone_aware_date",
        lambda tz: today,
    )

    value = await calculator.get_current_day_unrealized_pnl()
    assert value == trade.calculate_current_pnl_cents()


@pytest.mark.asyncio
async def test_get_current_day_unrealized_pnl_returns_zero_on_error(monkeypatch):
    store = FakeTradeStore()
    store.raise_on["get_trades_by_date_range"] = RuntimeError("redis offline")
    calculator = PnLCalculator(store)

    monkeypatch.setattr(
        "common.pnl_calculator_helpers.daily_operations.get_timezone_aware_date",
        lambda tz: date(2024, 1, 6),
    )

    value = await calculator.get_current_day_unrealized_pnl()
    assert value == 0


@pytest.mark.asyncio
async def test_generate_aggregated_report_by_close_date_empty(monkeypatch):
    monkeypatch.setattr(
        "common.pnl_calculator_helpers.reportgenerator_helpers.empty_report_factory.get_timezone_aware_date",
        lambda tz: date(2024, 1, 7),
    )
    monkeypatch.setattr(
        "common.pnl_calculator_helpers.reportgenerator_helpers.close_date_report_builder.get_timezone_aware_date",
        lambda tz: date(2024, 1, 7),
    )

    store = FakeTradeStore()
    calculator = PnLCalculator(store)

    report = await calculator.generate_aggregated_report_by_close_date([])

    assert report.total_trades == 0
    assert report.start_date == date(2024, 1, 7)


@pytest.mark.asyncio
async def test_generate_aggregated_report_by_close_date(monkeypatch):
    store = FakeTradeStore()
    earlier = datetime(2024, 1, 10, tzinfo=timezone.utc)
    later = datetime(2024, 1, 12, tzinfo=timezone.utc)
    trades = [
        _build_trade(settled=True),
        _build_trade(order_id="OID3", settled=True),
    ]
    trades[0].settlement_time = earlier
    trades[1].settlement_time = later
    store.trades_by_range = trades
    calculator = PnLCalculator(store)

    monkeypatch.setattr(
        "common.pnl_calculator_helpers.reportgenerator_helpers.close_date_report_builder.get_timezone_aware_date",
        lambda tz: date(2024, 1, 9),
    )
    report = await calculator.generate_aggregated_report_by_close_date(trades)

    assert report.start_date == earlier.date()
    assert report.end_date == later.date()
    assert report.total_trades == _TEST_COUNT_2


@pytest.mark.asyncio
async def test_generate_aggregated_report_by_close_date_raises_on_error():
    store = FakeTradeStore()
    trade = _build_trade()

    def _explode(self):
        raise RuntimeError("boom")

    trade.calculate_current_pnl_cents = MethodType(_explode, trade)

    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="boom"):
        await calculator.generate_aggregated_report_by_close_date([trade])


@pytest.mark.asyncio
async def test_generate_today_close_date_report(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade()
    store.closed_today_trades = [trade]
    calculator = PnLCalculator(store)

    report = await calculator.generate_today_close_date_report()
    assert report.total_trades == 1


@pytest.mark.asyncio
async def test_generate_today_close_date_report_propagates_errors():
    store = FakeTradeStore()
    store.raise_on["get_trades_closed_today"] = RuntimeError("fail")
    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="fail"):
        await calculator.generate_today_close_date_report()


@pytest.mark.asyncio
async def test_generate_yesterday_close_date_report_propagates_errors():
    store = FakeTradeStore()
    store.raise_on["get_trades_closed_yesterday"] = RuntimeError("fail")
    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="fail"):
        await calculator.generate_yesterday_close_date_report()


@pytest.mark.asyncio
async def test_generate_yesterday_close_date_report(monkeypatch):
    store = FakeTradeStore()
    store.closed_yesterday_trades = [_build_trade()]
    calculator = PnLCalculator(store)

    report = await calculator.generate_yesterday_close_date_report()
    assert report.total_trades == 1


@pytest.mark.asyncio
async def test_get_today_close_date_trades_and_report(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade()
    store.closed_today_trades = [trade]
    calculator = PnLCalculator(store)

    trades, report = await calculator.get_today_close_date_trades_and_report()
    assert trades == [trade]
    assert report.total_trades == 1


@pytest.mark.asyncio
async def test_get_today_close_date_trades_and_report_propagates_error():
    store = FakeTradeStore()
    store.raise_on["get_trades_closed_today"] = RuntimeError("boom")
    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="boom"):
        await calculator.get_today_close_date_trades_and_report()


@pytest.mark.asyncio
async def test_get_yesterday_close_date_trades_and_report(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade()
    store.closed_yesterday_trades = [trade]
    calculator = PnLCalculator(store)

    trades, report = await calculator.get_yesterday_close_date_trades_and_report()
    assert trades == [trade]
    assert report.total_trades == 1


@pytest.mark.asyncio
async def test_get_yesterday_close_date_trades_and_report_propagates_error():
    store = FakeTradeStore()
    store.raise_on["get_trades_closed_yesterday"] = RuntimeError("boom")
    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="boom"):
        await calculator.get_yesterday_close_date_trades_and_report()


@pytest.mark.asyncio
async def test_get_date_range_trades_and_report(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade()
    store.trades_by_range = {(date(2024, 1, 1), date(2024, 1, 2)): [trade]}
    calculator = PnLCalculator(store)

    trades, report = await calculator.get_date_range_trades_and_report(date(2024, 1, 1), date(2024, 1, 2))
    assert trades == [trade]
    assert report.total_trades == 1


@pytest.mark.asyncio
async def test_get_date_range_trades_and_report_propagates_error():
    store = FakeTradeStore()
    store.raise_on["get_trades_by_date_range"] = RuntimeError("range fail")
    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="range fail"):
        await calculator.get_date_range_trades_and_report(date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.asyncio
async def test_get_yesterday_unrealized_pnl(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade(pnl_offset=7)
    yesterday = date(2024, 1, 8)
    store.unrealized_trades[yesterday] = [trade]
    calculator = PnLCalculator(store)

    monkeypatch.setattr(
        "common.pnl_calculator_helpers.daily_operations.get_timezone_aware_date",
        lambda tz: yesterday + timedelta(days=1),
    )

    value = await calculator.get_yesterday_unrealized_pnl()
    assert value == trade.calculate_current_pnl_cents()


@pytest.mark.asyncio
async def test_get_yesterday_unrealized_pnl_returns_zero_on_error(monkeypatch):
    store = FakeTradeStore()
    store.raise_on["get_unrealized_trades_for_date"] = RuntimeError("oops")
    calculator = PnLCalculator(store)

    monkeypatch.setattr(
        "common.pnl_calculator_helpers.daily_operations.get_timezone_aware_date",
        lambda tz: date(2024, 1, 10),
    )

    value = await calculator.get_yesterday_unrealized_pnl()
    assert value == 0


@pytest.mark.asyncio
async def test_get_unrealized_pnl_snapshot_returns_none_when_missing():
    store = FakeTradeStore()
    calculator = PnLCalculator(store)

    value = await calculator.get_unrealized_pnl_snapshot(date(2024, 1, 11))
    assert value is None


@pytest.mark.asyncio
async def test_store_unrealized_pnl_snapshot_propagates_error():
    store = FakeTradeStore()
    store.raise_on["store_unrealized_pnl_data"] = RuntimeError("write error")
    calculator = PnLCalculator(store)

    with pytest.raises(RuntimeError, match="write error"):
        await calculator.store_unrealized_pnl_snapshot(date(2024, 2, 1), 500)


@pytest.mark.asyncio
async def test_get_unified_pnl_for_date(monkeypatch):
    store = FakeTradeStore()
    trade = _build_trade(pnl_offset=9)
    store.trades_by_range = {(date(2024, 1, 12), date(2024, 1, 12)): [trade]}
    calculator = PnLCalculator(store)

    value = await calculator.get_unified_pnl_for_date(date(2024, 1, 12))
    assert value == trade.calculate_current_pnl_cents()


@pytest.mark.asyncio
async def test_get_unified_pnl_for_date_returns_zero_on_error():
    store = FakeTradeStore()
    store.raise_on["get_trades_by_date_range"] = RuntimeError("fail unified")
    calculator = PnLCalculator(store)

    value = await calculator.get_unified_pnl_for_date(date(2024, 1, 13))
    assert value == 0


@pytest.mark.asyncio
async def test_get_today_unified_pnl(monkeypatch):
    store = FakeTradeStore()
    calculator = PnLCalculator(store)

    called = {}

    async def fake_get(date_value):
        called["date"] = date_value
        return 42

    calculator.unified_calc.get_unified_pnl_for_date = fake_get  # type: ignore[method-assign]
    monkeypatch.setattr(
        "common.pnl_calculator_helpers.unified_pnl_calculator.get_timezone_aware_date",
        lambda tz: date(2024, 1, 14),
    )

    value = await calculator.get_today_unified_pnl()
    assert value == _CONST_42
    assert called["date"] == date(2024, 1, 14)


@pytest.mark.asyncio
async def test_get_yesterday_unified_pnl(monkeypatch):
    store = FakeTradeStore()
    calculator = PnLCalculator(store)

    called = {}

    async def fake_get(date_value):
        called["date"] = date_value
        return 24

    calculator.unified_calc.get_unified_pnl_for_date = fake_get  # type: ignore[method-assign]
    monkeypatch.setattr(
        "common.pnl_calculator_helpers.unified_pnl_calculator.get_timezone_aware_date",
        lambda tz: date(2024, 1, 15),
    )

    value = await calculator.get_yesterday_unified_pnl()
    assert value == _CONST_24
    assert called["date"] == date(2024, 1, 14)


@pytest.mark.asyncio
async def test_update_daily_unrealized_pnl_handles_no_trades(monkeypatch):
    store = FakeTradeStore()
    store.trades_by_range = {(date(2024, 1, 16), date(2024, 1, 16)): []}
    calculator = PnLCalculator(store)

    monkeypatch.setattr("common.pnl_calculator.PnLCalculator.store_unrealized_pnl_snapshot", AsyncMock())

    value = await calculator.update_daily_unrealized_pnl(date(2024, 1, 16))
    assert value == 0


@pytest.mark.asyncio
async def test_update_daily_unrealized_pnl_propagates_error():
    store = FakeTradeStore()
    store.raise_on["store_unrealized_pnl_data"] = RuntimeError("persist fail")
    calculator = PnLCalculator(store)

    store.trades_by_range = {(date(2024, 1, 17), date(2024, 1, 17)): [_build_trade()]}

    with pytest.raises(RuntimeError, match="persist fail"):
        await calculator.update_daily_unrealized_pnl(date(2024, 1, 17))
