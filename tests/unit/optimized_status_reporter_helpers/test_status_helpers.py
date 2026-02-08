import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from common.data_conversion.micro_price_helpers.batch_converter import BatchConverter
from common.data_models.trading import OrderSide, OrderType
from common.deribit.utils import is_supported_ticker
from common.health.log_activity_monitor import LogActivityStatus
from common.monitoring import ProcessStatus
from common.optimized_status_reporter_helpers.data_coercion import DataCoercion
from common.optimized_status_reporter_helpers.day_night_detector import DayNightDetector
from common.optimized_status_reporter_helpers.health_snapshot_collector import (
    HealthSnapshotCollector,
)
from common.optimized_status_reporter_helpers.log_activity_formatter import (
    LogActivityFormatter,
)
from common.optimized_status_reporter_helpers.metrics_section_printer import (
    MetricsSectionPrinter,
)
from common.optimized_status_reporter_helpers.realtime_metrics_collector import (
    RealtimeMetricsCollector,
)
from common.optimized_status_reporter_helpers.section_printer import SectionPrinter
from common.optimized_status_reporter_helpers.service_printer import ServicePrinter
from common.optimized_status_reporter_helpers.service_status_formatter import (
    ServiceStatusFormatter,
)
from common.optimized_status_reporter_helpers.status_line_builder import (
    get_status_emoji,
    resolve_service_status,
)
from common.optimized_status_reporter_helpers.time_formatter import TimeFormatter
from common.optimized_status_reporter_helpers.weather_section_generator import (
    WeatherSectionGenerator,
)
from common.optimized_status_reporter_helpers.weather_temperature_collector import (
    WeatherTemperatureCollector,
    _build_temperature_map,
    _parse_station_weather,
)
from common.redis_protocol import SubscriptionUpdate
from common.time_utils.solar import calculate_solar_noon_utc, is_after_solar_noon
from common.trading.order_payloads import build_order_payload
from common.validation.probability import clamp_probability, first_valid_probability
from common.websocket.unified_subscription_manager_helpers.subscription_processor import (
    SubscriptionProcessor,
)
from common.websocket.unified_subscription_manager_helpers.update_handler import (
    UpdateHandler,
)


def test_status_line_builder_resolve_and_emoji():
    activity = SimpleNamespace(status=LogActivityStatus.ERROR)
    assert get_status_emoji(True, activity) == "🟡"
    assert get_status_emoji(False, None) == "🔴"

    tracker_status = {"enabled": False}
    bool_default = lambda v, d: bool(v) if v is not None else d
    result = resolve_service_status("tracker", None, False, tracker_status, bool_default)
    assert result == "Disabled" and tracker_status["running"] is False

    info_stopped = SimpleNamespace(status=ProcessStatus.STOPPED)
    assert resolve_service_status("svc", info_stopped, False, {}, lambda v, d: d) == "Stopped"
    assert resolve_service_status("svc", None, False, {}, lambda v, d: d) == "Unknown"
    assert resolve_service_status("svc", info_stopped, True, {}, lambda v, d: d) == "Active"


def test_section_printer_outputs_sections():
    lines: list[str] = []

    def emit(msg=None, **_kwargs):
        lines.append("" if msg is None else msg)

    printer = SectionPrinter(emit)

    printer.print_exchange_info("now", {"exchange_active": True, "trading_active": False})
    printer.print_exchange_info("now", {"error": "down"})
    printer.print_price_info({"btc_price": 10.0})

    class StubWeather:
        def generate_weather_section(self, status_data):
            return ["weather line"]

    printer.print_weather_info({}, StubWeather())
    printer.print_tracker_status_section(
        {"tracker_status": {"status_summary": "OK", "enabled": False, "running": False}},
        lambda v, d: v or d,
        lambda v, d: bool(d) if v is None else bool(v),
    )
    printer.print_tracker_status_section({}, lambda v, d: d, lambda v, d: d)

    # Ensure a reasonable number of lines were emitted across sections
    assert any("Exchange" in line for line in lines)
    assert any("Kalshi" in line for line in lines)
    assert any("Tracker status unavailable" in line for line in lines)


def test_metrics_section_printer_sections(monkeypatch):
    emitted: list[str] = []
    coercion = DataCoercion()
    printer = MetricsSectionPrinter(coercion)
    printer._emit_status_line = lambda message="": emitted.append(message)

    class StubWeatherSettings:
        class sources:
            asos_source = "OFF"

    monkeypatch.setattr(
        "common.optimized_status_reporter_helpers.metrics_section_printer.get_weather_settings",
        lambda: StubWeatherSettings(),
    )

    status_payload = {
        "deribit_messages_60s": "2",
        "kalshi_messages_60s": "3",
        "kalshi_market_status": {"trading_active": True},
        "cfb_messages_60s": 4,
        "asos_messages_65m": "5",
    }
    printer.print_all_health_sections(status_payload)
    assert any("Deribit" in line for line in emitted)
    assert any("ASOS" in line for line in emitted)


def test_weather_section_generator_and_service_status_formatter(monkeypatch):
    class StubDayNight:
        def __init__(self):
            self._station_coordinates = {"ABC": {"longitude": -10, "latitude": 0}}

        def get_day_night_icon(self, icao):
            return "🌙" if icao == "ABC" else ""

    class StubCoercion:
        @staticmethod
        def string_or_default(value, default):
            return value or default

    generator = WeatherSectionGenerator(StubDayNight(), StubCoercion())
    lines = generator.generate_weather_section({"ABC": {"temp_f": "70.1", "emoticon": "☀️"}, "BAD": "not-a-dict"})
    assert any("ABC" in line for line in lines)

    class StubResourceTracker:
        def get_process_resource_usage(self, service_name):
            return " CPU=1%"

    class StubLogFormatter:
        def format_age_only(self, activity):
            return "5s"

    formatter = ServiceStatusFormatter(StubResourceTracker(), StubLogFormatter())
    info = SimpleNamespace(status=ProcessStatus.STOPPED)
    tracker_status = {"enabled": True}
    line = formatter.build_service_status_line(
        "svc",
        info,
        False,
        tracker_status,
        SimpleNamespace(status=LogActivityStatus.RECENT, age_seconds=5, log_file_path=None),
    )
    assert "Stopped" in line and "CPU" in line
    tracker_line = formatter.build_service_status_line(
        "tracker",
        None,
        False,
        {"enabled": False},
        None,
    )
    assert "Disabled" in tracker_line


def test_service_printer_and_temperature_collector(monkeypatch):
    emitted: list[str] = []
    resource_tracker = SimpleNamespace(get_process_resource_usage=lambda name: "")
    log_formatter = SimpleNamespace(format_age_only=lambda activity: "", format_log_activity_short=lambda *_: "")
    printer = ServicePrinter(emitted.append, resource_tracker, log_formatter, lambda v, d: bool(v))

    class StubProcessManager:
        services = {"svc"}
        process_info = {"svc": SimpleNamespace(status=ProcessStatus.RUNNING)}

    printer.print_managed_services(
        StubProcessManager(),
        {"enabled": True, "running": True},
        {"svc": SimpleNamespace(status=LogActivityStatus.RECENT, age_seconds=1)},
    )
    assert emitted and "svc" in emitted[0]

    # Weather temperature helpers
    weather_map = _build_temperature_map(["ABC"], [{"temp_f": b"70", "weather_emoticon": b"sun"}])
    assert weather_map["ABC"]["temp_f"] == "70"
    assert _parse_station_weather({}) is None

    class StubPipeline:
        def __init__(self):
            self.calls = []

        def hgetall(self, key):
            self.calls.append(key)

        async def execute(self):
            return [{"temp_f": b"72", "weather_emoticon": b"sunny"}]

    class StubRedis:
        def __init__(self):
            self.pipeline_obj = StubPipeline()

        async def scan_iter(self, match=None, count=None):
            yield match.replace("*", "ABC")

        def pipeline(self):
            return self.pipeline_obj

    collector = WeatherTemperatureCollector(redis_client=StubRedis())
    temps = asyncio.run(collector.collect_weather_temperatures())
    assert "ABC" in temps


def test_probability_helpers():
    assert clamp_probability(1.2) == 1.0
    assert clamp_probability(-0.1) == 0.0
    assert clamp_probability("0.5") == 0.5
    assert clamp_probability(None) is None
    assert clamp_probability(float("nan")) is None

    assert first_valid_probability(None, "bad", 0.3) == 0.3
    assert first_valid_probability(None) is None


@pytest.mark.asyncio
async def test_subscription_processor_and_update_handler(monkeypatch):
    active = {}
    pending = [("inst", "type", "chan")]

    class StubWebsocket:
        def __init__(self):
            self.is_connected = True
            self.active_subscriptions = []

        async def subscribe(self, channels):
            self.active_subscriptions.extend(channels)
            return True

        async def unsubscribe(self, channels):
            for ch in channels:
                if ch in self.active_subscriptions:
                    self.active_subscriptions.remove(ch)

    ws = StubWebsocket()
    processor = SubscriptionProcessor("svc", ws, active, pending)
    await processor.process_pending()
    assert active == {"inst": {"api_type": "type"}}
    assert pending == []
    assert not processor.waiting_for_subscriptions

    # Update handler subscribe/unsubscribe
    pending_updates: list[tuple[str, str, str]] = []

    def api_mapper(name: str) -> str:
        return f"api-{name}"

    handler = UpdateHandler("svc", ws, active, pending_updates, api_mapper)

    subscribe_update = SubscriptionUpdate(name="new", subscription_type="instrument", action="subscribe")
    await handler.handle_update(subscribe_update, redis_client=None)
    assert pending_updates == [("new", "api-instrument", "new")]

    ws.active_subscriptions.append("inst")
    unsubscribe_update = SubscriptionUpdate(name="inst", subscription_type="instrument", action="unsubscribe")
    await handler.handle_update(unsubscribe_update, redis_client=None)
    assert "inst" not in active


def test_log_activity_and_time_formatting():
    tf = TimeFormatter()
    log_activity_formatter = LogActivityFormatter(tf)

    ok_activity = SimpleNamespace(status=LogActivityStatus.RECENT, age_seconds=65, log_file_path=None, error_message=None)
    assert log_activity_formatter.format_log_activity_short("svc", ok_activity).startswith("Recent")
    assert log_activity_formatter.format_age_only(ok_activity) == "1m 5s old"

    missing = SimpleNamespace(
        status=LogActivityStatus.NOT_FOUND,
        age_seconds=5,
        log_file_path="/tmp/log.txt",
        error_message=None,
    )
    assert "expected" in log_activity_formatter.format_log_activity_short("svc", missing)

    error_act = SimpleNamespace(
        status=LogActivityStatus.ERROR,
        age_seconds=-1,
        log_file_path=None,
        error_message="boom",
    )
    assert "boom" in log_activity_formatter.format_log_activity_short("svc", error_act)
    assert log_activity_formatter.format_age_only(error_act) is None


def test_day_night_detector_and_weather_helpers(monkeypatch):
    detector = DayNightDetector(moon_phase_calculator=SimpleNamespace(get_moon_phase_emoji=lambda: "🌙"))
    detector._station_coordinates = {"ABC": {"latitude": 0.0, "longitude": 0.0}}
    monkeypatch.setattr(
        "common.optimized_status_reporter_helpers.day_night_detector.is_between_dawn_and_dusk",
        lambda *_: False,
    )
    assert detector.get_day_night_icon("ABC") == "🌙"
    assert detector.get_day_night_icon("MISSING") == ""

    # Weather section generator already exercised above, ensure no errors on empty
    assert WeatherSectionGenerator(detector, DataCoercion()).generate_weather_section({}) == []


@pytest.mark.asyncio
async def test_realtime_metrics_collector(monkeypatch):
    import time as _time

    now_ts = _time.time()

    class StubRedis:
        def __init__(self, payload):
            self.payload = payload

        async def zrangebyscore(self, key, min_score, max_score, withscores=False):
            return self.payload

    entries = [
        (f"{int(now_ts)}|2.0", now_ts),
        ("bad", now_ts - 10),
    ]
    collector = RealtimeMetricsCollector(redis_client=StubRedis(entries))
    assert await collector.get_deribit_sum_last_60_seconds() == 2
    assert await collector.get_kalshi_sum_last_60_seconds() == 2

    # Error path
    class ErrorRedis:
        async def zrangebyscore(self, key, min_score, max_score, withscores=False):
            raise ConnectionError("boom")

    collector_err = RealtimeMetricsCollector(redis_client=ErrorRedis())
    assert await collector_err.get_deribit_sum_last_60_seconds() == 0


def test_health_snapshot_collector():
    class Check:
        def __init__(self, name, status):
            self.name = name
            self.status = status

    class StubChecker:
        async def check_all_health(self):
            return [
                Check("system_resources", "ok"),
                Check("redis_connectivity", "healthy"),
                Check("ldm_listener", "ok"),
            ]

    collector = HealthSnapshotCollector(StubChecker())
    snapshot = asyncio.run(collector.collect_health_snapshot())
    assert snapshot["system_resources_health"].name == "system_resources"
    assert snapshot["redis_connection_healthy"] is False  # status string not HealthStatus enum


def test_batch_converter_and_order_payloads():
    class StubOption:
        def __init__(self, valid):
            self.valid = valid
            self.strike = 1
            self.expiry = "2025"

        def is_valid(self):
            return self.valid

        def get_validation_errors(self):
            return "bad"

    def converter(instrument, currency):
        return StubOption(valid=instrument == "good")

    with pytest.raises(ValueError):
        BatchConverter.convert_instruments_to_micro_price_data([], "USD", converter)

    result = BatchConverter.convert_instruments_to_micro_price_data(["good", "bad"], "USD", converter)
    assert len(result) == 1

    order = SimpleNamespace(
        ticker="T",
        action=SimpleNamespace(value="buy"),
        side=OrderSide.YES,
        count=1,
        client_order_id="id",
        order_type=OrderType.LIMIT,
        time_in_force=SimpleNamespace(value="GTC"),
        yes_price_cents=10,
        expiration_ts=None,
    )
    payload = build_order_payload(order)
    assert payload["yes_price"] == 10
    bad_order = SimpleNamespace(**{**order.__dict__, "yes_price_cents": None})
    with pytest.raises(ValueError):
        build_order_payload(bad_order)


def test_solar_and_deribit_utils():
    date_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    solar_noon = calculate_solar_noon_utc(0, 0, date_now)
    assert solar_noon.tzinfo == timezone.utc
    assert isinstance(is_after_solar_noon(0, 0, solar_noon + timedelta(hours=1)), bool)

    assert is_supported_ticker("BTC_USDC")
    assert not is_supported_ticker("bad")
    assert not is_supported_ticker("BTC_USDC-EXTRA")
