import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from common.base_connection_manager_helpers import (
    backoff_calculator,
    lifecycle_helpers,
)
from common.base_connection_manager_helpers import notification_helpers as bcm_notification_helpers
from common.base_connection_manager_helpers import (
    retry_logic,
    state_broadcast_helper,
)
from common.connection_manager_helpers import health_monitor as cm_health_monitor
from common.connection_manager_helpers import notification_manager as cm_notification_manager
from common.connection_manager_helpers import reconnection_handler as cm_reconnection_handler
from common.connection_manager_helpers import state_manager as cm_state_manager
from common.connection_state import ConnectionState
from common.data_models.trade_record import TradeRecord, TradeSide
from common.metadata_store_helpers.data_normalizer import DataNormalizer
from common.optimized_status_reporter_helpers.data_formatting import DataFormatting
from common.optimized_status_reporter_helpers.moon_phase_calculator import (
    MoonPhaseCalculator,
)
from common.optimized_status_reporter_helpers.price_data_collector import (
    PriceDataCollector,
)
from common.optimized_status_reporter_helpers.redis_key_counter import RedisKeyCounter
from common.redis_protocol.trade_store.codec_helpers.decoder import decode_trade_record
from common.redis_protocol.trade_store.codec_helpers.encoder import (
    encode_trade_record,
    trade_record_to_payload,
)
from common.time_helpers.timestamp_parser import (
    MILLISECOND_TIMESTAMP_THRESHOLD,
    parse_timestamp,
)


class _DummyMetrics:
    def __init__(self, consecutive_failures: int = 0):
        self.consecutive_failures = consecutive_failures
        self.total_reconnection_attempts = 0


class _DummyMetricsTracker:
    def __init__(self, consecutive_failures: int = 0):
        self.metrics = _DummyMetrics(consecutive_failures)

    def get_metrics(self):
        return self.metrics

    def set_backoff_delay(self, delay: float):
        self.metrics.current_backoff_delay = delay

    def increment_total_connections(self):
        self.metrics.total_connections = getattr(self.metrics, "total_connections", 0) + 1


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None

    def exception(self, *_args, **_kwargs):
        return None


class _DummyManager:
    def __init__(self, consecutive_failures: int = 0):
        self.metrics_tracker = _DummyMetricsTracker(consecutive_failures)
        self.config = SimpleNamespace(
            reconnection_initial_delay_seconds=1.0,
            reconnection_backoff_multiplier=2.0,
            reconnection_max_delay_seconds=10.0,
            max_consecutive_failures=2,
        )
        self.logger = _DummyLogger()
        self.shutdown_requested = False
        self.state = ConnectionState.DISCONNECTED
        self.service_name = "svc"
        self.health_check_task = None
        self.reconnection_task = None
        self.state_tracker = None
        self._state_tracker_initializer = self._initialize_state_tracker

    async def connect_with_retry(self):
        # Simulate a single successful connection attempt
        self.metrics_tracker.metrics.consecutive_failures = 0
        return True

    async def start_health_monitoring(self):
        return None

    async def cleanup_connection(self):
        return None

    def transition_state(self, new_state, _ctx=None):
        self.state = new_state

    async def _initialize_state_tracker(self):
        self.state_tracker_initialized = True

    async def _state_manager_broadcast(self, *_args, **_kwargs):
        self.broadcast_called = True

    def calculate_backoff_delay(self):
        return 0.0


def _build_trade(**overrides):
    base = dict(
        order_id="1",
        market_ticker="TICKER",
        trade_timestamp=datetime.now(timezone.utc),
        trade_side=TradeSide.YES,
        quantity=1,
        price_cents=50,
        fee_cents=1,
        cost_cents=51,
        market_category="binary",
        trade_rule="rule",
        trade_reason="descriptive reason",
    )
    base.update(overrides)
    return TradeRecord(**base)


def test_data_normalizer_fields_and_numeric_coercion():
    raw = {b"count": b"5", "price": "10.5", "flag": True, "empty": "   "}
    normalized = DataNormalizer.normalize_hash(raw)
    assert normalized["count"] == "5"

    assert DataNormalizer.int_field(normalized, "count") == 5
    assert DataNormalizer.int_field(normalized, "flag") == 1
    assert DataNormalizer.int_field(normalized, "missing", value_on_error=7) == 7

    assert DataNormalizer.float_field(normalized, "price") == 10.5
    assert DataNormalizer.float_field(normalized, "empty", value_on_error=2.5) == 2.5
    with pytest.raises(ValueError):
        DataNormalizer.int_field({"price": object()}, "price")
    with pytest.raises(ValueError):
        DataNormalizer.float_field({"price": object()}, "price")


def test_timestamp_parser_handles_types_and_errors():
    now = datetime.now(timezone.utc)
    assert parse_timestamp(now) == now

    parsed = parse_timestamp(MILLISECOND_TIMESTAMP_THRESHOLD + 1000)
    assert parsed.tzinfo == timezone.utc

    iso = "2024-01-01T00:00:00"
    parsed_iso = parse_timestamp(iso)
    assert parsed_iso.tzinfo == timezone.utc

    assert parse_timestamp(b"2024-01-02T00:00:00Z") is not None
    assert parse_timestamp(None, allow_none=True) is None
    with pytest.raises(TypeError):
        parse_timestamp({"bad": "type"})


def test_data_formatting_and_moon_phase():
    assert DataFormatting.format_percentage(None) == "N/A"
    assert DataFormatting.format_percentage(True) == "1.0%"
    assert DataFormatting.format_percentage("12.34") == "12.3%"
    assert DataFormatting.format_percentage("bad") == "N/A"

    # Moon phase should return a single emoji even if calculation fails
    emoji = MoonPhaseCalculator.get_moon_phase_emoji()
    assert isinstance(emoji, str) and emoji


@pytest.mark.asyncio
async def test_price_data_collector_and_redis_key_counter(monkeypatch):
    class StubStore:
        def __init__(self, _client):
            pass

        async def get_usdc_micro_price(self, ticker):
            if ticker == "BTC":
                return 10.0
            raise RuntimeError("fail")

    monkeypatch.setattr(
        "common.redis_protocol.market_store.DeribitStore",
        StubStore,
    )

    collector = PriceDataCollector(redis_client="redis")
    prices = await collector.collect_price_data()
    assert prices == {"btc_price": 10.0, "eth_price": None}

    class StubRedis:
        def __init__(self, keys):
            self._keys = keys

        async def scan_iter(self, match=None, count=None):
            prefix = match.split(":*", 1)[0] if match else ""
            for key in self._keys:
                if not prefix or key.startswith(prefix):
                    yield key

    class StubSchema:
        deribit_market_prefix = "deribit"
        kalshi_market_prefix = "kalshi"

    monkeypatch.setattr(
        "common.optimized_status_reporter_helpers.redis_key_counter.get_schema_config",
        lambda: StubSchema(),
    )

    redis_client = StubRedis(["deribit:a", "kalshi:b", "cfb:c", "weather:station:x"])
    counter = RedisKeyCounter(redis_client)
    counts = await counter.collect_key_counts()
    assert counts["redis_deribit_keys"] == 1
    assert counts["redis_kalshi_keys"] == 1
    assert counts["redis_cfb_keys"] == 1
    assert counts["redis_weather_keys"] == 1


@pytest.mark.asyncio
async def test_backoff_and_retry_and_lifecycle_helpers(monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.5)
    mgr_for_delay = _DummyManager(consecutive_failures=2)
    delay = backoff_calculator.calculate_backoff_delay(mgr_for_delay)
    assert delay >= 0

    mgr = _DummyManager(consecutive_failures=1)
    notifications: list[tuple[bool, str]] = []

    async def notify(is_connected: bool, details: str = ""):
        notifications.append((is_connected, details))

    async def establish():
        return True

    def transition(state, error_context=None):
        mgr.state = state

    async def fake_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(retry_logic.asyncio, "sleep", fake_sleep)
    assert await retry_logic.connect_with_retry(mgr, establish, notify, transition)
    assert notifications and notifications[-1][0]

    started = await lifecycle_helpers.start_connection_manager(mgr)
    assert started and mgr.health_check_task
    mgr.reconnection_task = asyncio.create_task(asyncio.sleep(0))
    await lifecycle_helpers.stop_connection_manager(mgr)


@pytest.mark.asyncio
async def test_notification_and_state_helpers(monkeypatch):
    mgr = _DummyManager()
    mgr.notification_handler = SimpleNamespace(send_connection_notification=lambda *_args, **_kwargs: asyncio.sleep(0))
    mgr.state_tracker = SimpleNamespace(store_service_metrics=lambda *_args, **_kwargs: asyncio.sleep(0))
    await bcm_notification_helpers.send_connection_notification(mgr, True, "ok")

    # broadcast helper should initialize tracker on demand
    manager = _DummyManager()
    await state_broadcast_helper.broadcast_state_change(manager, ConnectionState.READY)
    await state_broadcast_helper.initialize_state_tracker(manager)


def test_connection_manager_helper_stubs():
    # These helper classes are thin wrappers; ensure constructors and methods are reachable
    hm = cm_health_monitor.HealthMonitor()
    assert asyncio.run(hm.monitor()) is None

    nm = cm_notification_manager.NotificationManager(foo="bar")
    assert nm._shutdown_requested is False
    # notify is a stub that raises NotImplementedError
    with pytest.raises(NotImplementedError):
        asyncio.run(nm.notify())

    rm = cm_reconnection_handler.ReconnectionHandler()
    with pytest.raises(NotImplementedError):
        asyncio.run(rm.reconnect())

    sm = cm_state_manager.StateManager(foo="bar")
    with pytest.raises(NotImplementedError):
        asyncio.run(sm.transition_state())


def test_trade_record_codec_roundtrip():
    trade = _build_trade(price_cents=50, cost_cents=51)
    payload = trade_record_to_payload(trade)
    encoded = encode_trade_record(trade)
    decoded = decode_trade_record(encoded)

    assert payload["order_id"] == decoded.order_id
    assert decoded.trade_side is TradeSide.YES
    assert decoded.trade_timestamp.tzinfo == timezone.utc
