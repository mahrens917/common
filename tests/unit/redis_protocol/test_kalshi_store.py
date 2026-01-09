from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import orjson
import pytest

import common.redis_protocol.kalshi_store as kalshi_store_module
import common.redis_protocol.market_normalization as normalization_module
from common.redis_protocol.kalshi_store import KalshiStore, KalshiStoreError
from common.redis_protocol.kalshi_store.store_initializer import initialize_kalshi_store
from common.redis_protocol.market_normalization import (
    convert_numeric_field,
    derive_expiry_iso,
    derive_strike_fields,
    ensure_market_metadata_fields,
    format_probability_value,
    normalise_hash,
    normalize_timestamp,
    parse_expiry_token,
    select_timestamp_value,
    sync_top_of_book_fields,
)
from common.redis_protocol.market_normalization_core import ProbabilityValueError

_CONST_2025 = 2025
_TEST_COUNT_10 = 10
_TEST_COUNT_2 = 2
_TEST_COUNT_3 = 3
_TEST_COUNT_5 = 5
_TEST_COUNT_8 = 8
_TEST_ID_123 = 123
_VAL_0_25 = 0.25
_VAL_0_3 = 0.3
_VAL_0_45 = 0.45
_VAL_0_5 = 0.5
_VAL_0_55 = 0.55
_VAL_1_25 = 1.25
_VAL_30_0 = 30.0
_VAL_5_0 = 5.0

from common.redis_protocol.retry import (
    RedisFatalError,
    RedisRetryContext,
    RedisRetryError,
)
from common.redis_protocol.weather_station_resolver import WeatherStationResolver
from common.redis_schema import build_kalshi_market_key


@pytest.fixture
def store(fake_redis):
    """Lightweight KalshiStore wired to the in-memory FakeRedis."""
    logger_instance = logging.getLogger("tests.kalshi_store")

    # Provide station mappings for test tickers
    station_mapping = {
        "CHI": {"icao": "KORD", "name": "Chicago O'Hare"},
        "NYC": {"icao": "KJFK", "name": "New York JFK"},
    }
    weather_resolver = WeatherStationResolver(lambda: station_mapping, logger=logger_instance)

    # Use proper __init__ to ensure _attr_resolver and all delegators are initialized
    instance = KalshiStore(redis=fake_redis, service_prefix="ws", weather_resolver=weather_resolver)

    return instance


def test_convert_numeric_field_variants():
    assert convert_numeric_field(" 1.25 ") == _VAL_1_25
    assert convert_numeric_field(5) == _VAL_5_0
    assert convert_numeric_field("") is None
    assert convert_numeric_field(None) is None
    with pytest.raises((ValueError, TypeError)):
        convert_numeric_field(["bad"])


def test_format_probability_value_normalises_decimal():
    result = format_probability_value("0.5000")
    assert result == "0.5"


def test_format_probability_value_rejects_invalid_input():
    with pytest.raises(ProbabilityValueError):
        format_probability_value("not-a-number")
    with pytest.raises(ProbabilityValueError):
        format_probability_value(float("inf"))


def test_normalise_hash_decodes_bytes(store: KalshiStore):
    raw = {b"foo": b"bar", "baz": "qux"}
    normalised = normalise_hash(raw)
    assert normalised == {"foo": "bar", "baz": "qux"}


def test_sync_top_of_book_fields_populates_scalars():
    snapshot = {
        "yes_bids": json.dumps({"0.45": 10}),
        "yes_asks": json.dumps({"0.55": 5}),
    }
    sync_top_of_book_fields(snapshot)
    assert snapshot["yes_bid"] == "0.45"
    assert snapshot["yes_bid_size"] == "10"
    assert snapshot["yes_ask"] == "0.55"
    assert snapshot["yes_ask_size"] == "5"


@pytest.mark.asyncio
async def test_store_optional_field_handles_present_and_missing(store: KalshiStore):
    redis = store.redis
    await redis.hset("market:foo", "field", "value")
    await store._store_optional_field(redis, "market:foo", "field", None)
    assert "field" not in redis.dump_hash("market:foo")

    await store._store_optional_field(redis, "market:foo", "field", 1.23)
    assert redis.dump_hash("market:foo")["field"] == "1.23"


@pytest.mark.parametrize(
    "token,expect_year",
    [
        ("25AUG31", 2025),
        ("14SEP1530", 2024),
        ("15OCT26", 2015),
    ],
)
def test_parse_expiry_token_variants(monkeypatch, token, expect_year):
    base_now = datetime(2024, 9, 13, 12, 0, tzinfo=timezone.utc)
    parsed = parse_expiry_token(token, now=base_now)
    assert parsed is not None
    assert parsed.year == expect_year


def test_parse_expiry_token_invalid(monkeypatch):
    monkeypatch.setattr(normalization_module, "datetime", datetime)
    assert parse_expiry_token("bad") is None


def test_derive_strike_fields_variations():
    assert derive_strike_fields("KXHIGH-FOO-B80") == (
        "less",
        None,
        80.0,
        80.0,
    )
    assert derive_strike_fields("KXHIGH-FOO-T90") == (
        "greater",
        90.0,
        None,
        90.0,
    )
    assert derive_strike_fields("KXHIGH-FOO-M100") == (
        "between",
        None,
        None,
        100.0,
    )
    assert derive_strike_fields("KXHIGH-20240101-KNYC-BETWEEN-70-90") == (
        "between",
        70.0,
        90.0,
        90.0,
    )
    assert derive_strike_fields("KXHIGH-FOO-???") is None


def test_ensure_market_metadata_fields_enriches_missing_values(store: KalshiStore):
    ticker = "KXHIGHCHI-25AUG31-B80"
    metadata = {"close_time_ms": 1_700_000_000_000}
    descriptor = store._market_descriptor(ticker)
    enriched = ensure_market_metadata_fields(
        ticker,
        metadata,
        descriptor=descriptor,
        token_parser=parse_expiry_token,
    )

    assert enriched["ticker"] == ticker
    assert enriched["strike_type"] == "less"
    assert enriched["cap_strike"] == "80.0"
    assert enriched["floor_strike"] == "0"
    assert enriched["close_time"].endswith("+00:00")
    assert enriched["status"] == "open"
    assert enriched["yes_bids"] == "{}"
    assert enriched["yes_asks"] == "{}"


@pytest.mark.parametrize(
    "value,expected",
    [
        (1_700_000_000, "2023-11-14T22:13:20+00:00"),
        ("2024-02-01T12:00:00Z", "2024-02-01T12:00:00+00:00"),
        ("not-iso", "not-iso"),
    ],
)
def test_normalize_timestamp_handles_int_and_str(value, expected):
    assert normalize_timestamp(value) == expected


def test_derive_expiry_iso_prefers_metadata(monkeypatch, store: KalshiStore):
    descriptor = SimpleNamespace(expiry_token=None, key="key", ticker="ticker")
    monkeypatch.setattr(store, "_market_descriptor", lambda _: descriptor)
    metadata = {"close_time": "2024-02-01T12:00:00Z"}
    assert (
        derive_expiry_iso(
            "TICKER",
            metadata,
            descriptor=descriptor,
            token_parser=parse_expiry_token,
        )
        == "2024-02-01T12:00:00Z"
    )


def test_derive_expiry_iso_uses_token(monkeypatch, store: KalshiStore):
    descriptor = SimpleNamespace(
        expiry_token="25AUG31",
        key="key",
        ticker="ticker",
    )
    monkeypatch.setattr(store, "_market_descriptor", lambda _: descriptor)
    result = derive_expiry_iso(
        "TICKER",
        {},
        descriptor=descriptor,
        token_parser=parse_expiry_token,
    )
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed.year == _CONST_2025


def test_derive_expiry_iso_uses_future_timestamp(monkeypatch, store: KalshiStore):
    base_now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    descriptor = SimpleNamespace(expiry_token=None, key="key", ticker="ticker")
    monkeypatch.setattr(store, "_market_descriptor", lambda _: descriptor)

    future_ts = base_now + timedelta(hours=2)
    result = derive_expiry_iso(
        "TICKER",
        {"timestamp": str(future_ts.timestamp())},
        descriptor=descriptor,
        token_parser=parse_expiry_token,
        now=base_now,
    )
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed == future_ts


def test_weather_resolver_direct_match():
    resolver = WeatherStationResolver(lambda: {"PHIL": {"icao": "KPHL"}}, logger=logging.getLogger("tests.weather"))
    assert resolver.extract_station("KXHIGHPHIL-25AUG31-B80.5") == "KPHL"


def test_weather_resolver_alias_resolution():
    resolver = WeatherStationResolver(
        lambda: {"AUS": {"icao": "KAUS", "aliases": ["HAUS"]}},
        logger=logging.getLogger("tests.weather"),
    )
    assert resolver.extract_station("KXHIGHHAUS-25AUG30-T100") == "KAUS"


def test_weather_resolver_non_kxhigh():
    resolver = WeatherStationResolver(lambda: {}, logger=logging.getLogger("tests.weather"))
    assert resolver.extract_station("OTHER-25AUG31") is None


def test_get_market_key_uses_descriptor(monkeypatch, store: KalshiStore):
    # The implementation uses KalshiMarketKey which normalizes to uppercase
    assert store.get_market_key("ticker") == "markets:kalshi:custom:TICKER"


def test_weather_resolver_resolve_city_alias():
    resolver = WeatherStationResolver(
        lambda: {"NY": {"icao": "KNYC", "aliases": ["NEWYORK"]}},
        logger=logging.getLogger("tests.weather"),
    )
    assert resolver.resolve_city_alias("NEWYORK") == "NY"
    assert resolver.resolve_city_alias("UNKNOWN") is None


@pytest.fixture
def connection_store():
    logger_instance = logging.getLogger("tests.kalshi_store.connection")
    weather_resolver = WeatherStationResolver(lambda: {}, logger=logger_instance)

    # Use proper __init__ to ensure _attr_resolver and all delegators are initialized
    instance = KalshiStore(redis=None, service_prefix="ws", weather_resolver=weather_resolver)

    return instance


def test_resolve_connection_settings_logs_masked_password(monkeypatch):
    dummy_resolver = WeatherStationResolver(lambda: {}, logger=logging.getLogger("tests"))
    monkeypatch.setattr(kalshi_store_module, "REDIS_PASSWORD", "very-secret")
    store = KalshiStore(weather_resolver=dummy_resolver)
    mock_logger = Mock(spec=logging.Logger)
    store._connection._logger = mock_logger
    store._connection_settings = None
    store._connection_settings_logged = False

    settings = store._resolve_connection_settings()
    assert settings["host"] == kalshi_store_module.REDIS_HOST
    assert settings["password"] == "very-secret"

    first_call = mock_logger.info.call_args
    assert first_call is not None
    assert first_call[0][0].startswith("Resolved Redis connection settings")
    assert first_call[0][1]["password"] == "***"

    mock_logger.info.reset_mock()
    store._resolve_connection_settings()
    mock_logger.info.assert_not_called()


@pytest.mark.asyncio
async def test_acquire_pool_reuses_existing_client(connection_store, fake_redis):
    connection_store.redis = fake_redis
    connection_store._connection_settings = {}
    connection_store._connection_settings_logged = True

    redis_client = await connection_store._acquire_pool(allow_reuse=True)
    assert redis_client is fake_redis


@pytest.mark.asyncio
async def test_acquire_pool_creates_new_client_when_forced(monkeypatch, connection_store):
    old_client = SimpleNamespace(name="old")
    connection_store.redis = old_client
    connection_store._connection_settings = {}
    connection_store._connection_settings_logged = True

    close_mock = AsyncMock()
    monkeypatch.setattr(connection_store._connection._pool_manager, "close_redis_client", close_mock, raising=False)

    new_client = SimpleNamespace(name="new")

    async def fake_create():
        connection_store.redis = new_client
        return new_client

    monkeypatch.setattr(
        connection_store._connection._pool_manager,
        "create_redis_client",
        fake_create,
        raising=False,
    )

    result = await connection_store._acquire_pool(allow_reuse=False)
    assert result is new_client
    close_mock.assert_awaited_once_with(old_client)


@pytest.mark.asyncio
async def test_connect_with_retry_retries_then_succeeds(monkeypatch, connection_store):
    attempts: list[bool] = []
    clients = [SimpleNamespace(name="first"), SimpleNamespace(name="second")]

    async def fake_acquire(*, allow_reuse: bool, redis, close_callback):
        attempts.append(allow_reuse)
        client = clients.pop(0)
        return client

    monkeypatch.setattr(
        connection_store._connection._pool_manager,
        "acquire_pool",
        fake_acquire,
        raising=False,
    )

    verify_results = [(False, False), (True, False)]

    async def fake_verify(_redis):
        return verify_results.pop(0)

    monkeypatch.setattr(
        connection_store._connection._connection_verifier,
        "verify_connection",
        fake_verify,
        raising=False,
    )

    close_mock = AsyncMock()
    monkeypatch.setattr(
        connection_store._connection._pool_manager,
        "close_redis_client",
        close_mock,
        raising=False,
    )

    ok = await connection_store._connect_with_retry(
        allow_reuse=False,
        context="test",
        attempts=2,
        retry_delay=0.01,
    )

    assert ok is True
    assert connection_store._initialized is True
    assert attempts == [False, False]
    assert close_mock.await_count >= 1


@pytest.mark.asyncio
async def test_connect_with_retry_returns_false_after_failures(monkeypatch, connection_store):
    clients = [SimpleNamespace(name="first"), SimpleNamespace(name="second")]

    async def fake_acquire(*, allow_reuse: bool, redis, close_callback):
        client = clients.pop(0)
        return client

    monkeypatch.setattr(
        connection_store._connection._pool_manager,
        "acquire_pool",
        fake_acquire,
        raising=False,
    )

    async def fake_verify(_redis):
        return False, False

    monkeypatch.setattr(
        connection_store._connection._connection_verifier,
        "verify_connection",
        fake_verify,
        raising=False,
    )

    close_mock = AsyncMock()
    monkeypatch.setattr(
        connection_store._connection._pool_manager,
        "close_redis_client",
        close_mock,
        raising=False,
    )

    ok = await connection_store._connect_with_retry(
        allow_reuse=True,
        context="test",
        attempts=2,
        retry_delay=0.01,
    )

    assert ok is False
    assert connection_store._initialized is False
    assert connection_store.redis is None
    assert close_mock.await_count == _TEST_COUNT_2


@pytest.mark.asyncio
async def test_ensure_connection_uses_existing_client(connection_store, fake_redis):
    connection_store.redis = fake_redis
    ok = await connection_store._ensure_redis_connection()
    assert ok is True
    assert connection_store._initialized is True


@pytest.mark.asyncio
async def test_ensure_connection_creates_new_client(monkeypatch, connection_store):
    created = {}

    class DummyRedis:
        def __init__(self):
            created["called"] = True
            self.connection_pool = "POOL"
            self._closed = False

        async def ping(self):
            return True

    async def fake_get_redis_client():
        return DummyRedis()

    # Monkeypatch the canonical get_redis_client from connection_pool_core
    import common.redis_protocol.connection_pool_core as pool_core

    monkeypatch.setattr(pool_core, "get_redis_client", fake_get_redis_client)

    ok = await connection_store._ensure_redis_connection()
    assert ok is True
    assert connection_store.redis is not None
    assert connection_store._initialized is True
    assert created["called"] is True
    assert connection_store.redis.connection_pool == "POOL"


@pytest.mark.asyncio
async def test_ensure_connection_failure(monkeypatch, connection_store):
    class FailingRedis:
        def __init__(self):
            self.connection_pool = "POOL"

        async def ping(self):
            raise RuntimeError("boom")

    async def fake_get_redis_client():
        return FailingRedis()

    # Monkeypatch the canonical get_redis_client from connection_pool_core
    import common.redis_protocol.connection_pool_core as pool_core

    monkeypatch.setattr(pool_core, "get_redis_client", fake_get_redis_client)

    ok = await connection_store._ensure_redis_connection()
    assert ok is False
    assert connection_store._initialized is False


@pytest.mark.asyncio
async def test_get_redis_reestablishes_connection(monkeypatch, connection_store, fake_redis):
    connection_store.redis = None
    connection_store._initialized = False
    ensure = AsyncMock(return_value=True)
    connection_store._ensure_redis_connection = ensure  # type: ignore[assignment]
    connection_store.redis = fake_redis
    result = await connection_store._get_redis()
    assert result is fake_redis
    ensure.assert_awaited()


@pytest.mark.asyncio
async def test_get_redis_raises_when_reconnect_fails(monkeypatch, connection_store):
    connection_store.redis = None
    connection_store._initialized = False
    connection_store._ensure_redis_connection = AsyncMock(return_value=False)  # type: ignore[assignment]
    with pytest.raises(RuntimeError):
        await connection_store._get_redis()


@pytest.mark.asyncio
async def test_close_invokes_cleanup(monkeypatch, connection_store, fake_redis):
    cleaned = {}

    async def fake_cleanup():
        cleaned["called"] = True

    monkeypatch.setattr(kalshi_store_module, "cleanup_redis_pool", fake_cleanup)
    connection_store._pool = "POOL"
    connection_store.redis = fake_redis
    await connection_store.close()
    assert cleaned.get("called") is True
    assert connection_store._pool is None
    assert connection_store.redis is None


def _build_market_data(strike_type: str) -> dict:
    base = {
        "id": "market-1",
        "strike_type": strike_type,
        "floor_strike": 80,
        "cap_strike": 120,
        "close_time": "2024-02-01T12:00:00Z",
        "open_time": "2024-01-01T09:00:00Z",
        "can_close_early": True,
        "tick_size": 1,
        "event_id": "event-1",
        "series_id": "series-1",
        "volume": 12,
    }
    return base


def test_build_kalshi_metadata_formats_fields(monkeypatch, store: KalshiStore):
    monkeypatch.setattr(kalshi_store_module.time, "time", lambda: 1_700_000_000)
    store.weather_resolver = WeatherStationResolver(lambda: {"CHI": {"icao": "KORD"}}, logger=store.logger)
    market_ticker = "KXHIGHCHI-25AUG31-B80"
    market_data = _build_market_data("less")
    event_data = {
        "ticker": "EVT",
        "title": "Event Title",
        "mutually_exclusive": True,
        "tags": ["a", "b"],
    }

    metadata = store._build_kalshi_metadata(market_ticker, market_data, event_data)
    assert metadata["market_ticker"] == "KXHIGHCHI-25AUG31-B80"
    assert metadata["floor_strike"] == "0"
    assert metadata["cap_strike"] == "120"
    assert metadata["can_close_early"] == "true"
    # Orderbook fields (yes_bids, yes_asks, etc) are not set by REST -
    # they come exclusively from websocket snapshots/deltas
    assert "yes_bids" not in metadata
    assert metadata["event_ticker"] == "EVT"
    assert metadata["event_tags"] == "['a', 'b']"
    assert metadata["weather_station"] == "KORD"
    assert metadata["timestamp"] == str(1_700_000_000)


def test_build_kalshi_metadata_between_strike(store: KalshiStore):
    market_ticker = "KXHIGHCHI-25AUG31-M100"
    market_data = _build_market_data("between")
    metadata = store._build_kalshi_metadata(market_ticker, market_data, None)
    assert metadata["floor_strike"] == "80"
    assert metadata["cap_strike"] == "120"


def test_select_timestamp_value_prefers_first():
    data = {"close_time": "", "close_time_ts": 123, "supplemental": 456}
    selected = select_timestamp_value(data, ["close_time", "close_time_ts", "supplemental"])
    assert selected == _TEST_ID_123


def test_ensure_market_metadata_fields_between_with_orderbook(store: KalshiStore):
    ticker = "KXHIGHCHI-25AUG31-M100"
    metadata = {
        "yes_bids": json.dumps({"0.51": 4}),
        "yes_asks": json.dumps({"0.61": 2}),
        "status": "halted",
    }
    descriptor = store._market_descriptor(ticker)
    enriched = ensure_market_metadata_fields(
        ticker,
        metadata,
        descriptor=descriptor,
        token_parser=parse_expiry_token,
    )
    assert enriched["strike_type"] == "between"
    sync_top_of_book_fields(enriched)
    assert enriched["yes_bid"] == "0.51"
    assert enriched["yes_ask"] == "0.61"
    assert enriched["status"] == "halted"


@pytest.mark.asyncio
async def test_subscription_lifecycle_ws(monkeypatch, store: KalshiStore, fake_redis):
    monkeypatch.setattr(store, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]
    await store.add_subscribed_market("BTC-M1")
    await store.add_subscribed_market("BTC-M2")
    markets = await store.get_subscribed_markets()
    assert markets == {"BTC-M1", "BTC-M2"}
    await store.remove_subscribed_market("BTC-M1")
    markets_after = await store.get_subscribed_markets()
    assert markets_after == {"BTC-M2"}


@pytest.mark.asyncio
async def test_subscription_ids_for_prefix(monkeypatch, fake_redis):
    logger_ws = logging.getLogger("tests.kalshi_store.subs.ws")
    weather_resolver_ws = WeatherStationResolver(lambda: {}, logger=logger_ws)

    store_ws = object.__new__(KalshiStore)
    initialize_kalshi_store(store_ws, fake_redis, "ws", weather_resolver_ws)
    monkeypatch.setattr(store_ws, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]

    await store_ws.record_subscription_ids({"BTC-M1": 123, "ETH-M2": None})
    recovered = await store_ws.fetch_subscription_ids(market_tickers=["BTC-M1", "ETH-M2"])
    assert recovered == {"BTC-M1": "123"}
    await store_ws.clear_subscription_ids(market_tickers=["BTC-M1"])
    recovered_after = await store_ws.fetch_subscription_ids(market_tickers=["BTC-M1"])
    assert recovered_after == {}

    # Repeat for REST prefix
    logger_rest = logging.getLogger("tests.kalshi_store.subs.rest")
    weather_resolver_rest = WeatherStationResolver(lambda: {}, logger=logger_rest)

    store_rest = object.__new__(KalshiStore)
    initialize_kalshi_store(store_rest, fake_redis, "rest", weather_resolver_rest)
    monkeypatch.setattr(store_rest, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]

    await store_rest.record_subscription_ids({"BTC-M3": 999})
    recovered_rest = await store_rest.fetch_subscription_ids(market_tickers=["BTC-M3"])
    assert recovered_rest == {"BTC-M3": "999"}


@pytest.mark.asyncio
async def test_service_status_helpers(monkeypatch, store: KalshiStore):
    monkeypatch.setattr(store, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]
    await store.update_service_status("kalshi", {"status": "healthy"})
    assert store.redis.dump_hash("status")["kalshi"] == "healthy"

    status = await store.get_service_status("kalshi")
    assert status == "healthy"


@pytest.mark.asyncio
async def test_process_orderbook_snapshot_updates_hash(store: KalshiStore, fake_redis):
    store.redis = fake_redis
    calls: list[tuple[str, float, float]] = []

    async def fake_update(ticker: str, bid: float | None, ask: float | None) -> None:
        calls.append((ticker, bid or 0.0, ask or 0.0))

    store._update_trade_prices_for_market = fake_update  # type: ignore[assignment]

    msg_data = {"yes": [[45.5, 10], [44.0, 5]], "no": [[60.0, 2]]}
    market_ticker = "TICK-SNAP"
    market_key = store.get_market_key(market_ticker)

    result = await store._process_orderbook_snapshot(
        redis=fake_redis,
        market_key=market_key,
        market_ticker=market_ticker,
        msg_data=msg_data,
        timestamp="1700000000",
    )

    assert result is True
    stored = await fake_redis.hgetall(market_key)
    assert orjson.loads(stored["yes_bids"]) == {"45.5": 10, "44.0": 5}
    assert orjson.loads(stored["yes_asks"]) == {"40.0": 2}
    assert stored["timestamp"] == "1700000000"
    assert await fake_redis.hget(market_key, "yes_bid") == "45.5"
    assert await fake_redis.hget(market_key, "yes_ask") == "40.0"
    assert calls == [("TICK-SNAP", 45.5, 40.0)]


@pytest.mark.asyncio
async def test_process_orderbook_snapshot_skips_when_empty(store: KalshiStore, fake_redis):
    result = await store._process_orderbook_snapshot(
        redis=fake_redis,
        market_key="book:key",
        market_ticker="TICK-EMPTY",
        msg_data={},
        timestamp="0",
    )
    assert result is True
    assert await fake_redis.hgetall("book:key") == {}


@pytest.mark.asyncio
async def test_process_orderbook_delta_updates_levels(store: KalshiStore, fake_redis):
    market_ticker = "TICK-DELTA"
    market_key = store.get_market_key(market_ticker)
    await fake_redis.hset(
        market_key,
        mapping={
            "yes_bids": orjson.dumps({"45.5": 10}).decode(),
            "yes_asks": orjson.dumps({"40.0": 2}).decode(),
            "yes_bid": "45.5",
            "yes_ask": "40.0",
            "yes_bid_size": "10",
            "yes_ask_size": "2",
        },
    )

    calls: list[tuple[str, float, float]] = []

    async def fake_update(ticker: str, bid: float | None, ask: float | None) -> None:
        calls.append((ticker, bid or 0.0, ask or 0.0))

    store._update_trade_prices_for_market = fake_update  # type: ignore[assignment]

    result_yes = await store._process_orderbook_delta(
        redis=fake_redis,
        market_key=market_key,
        market_ticker=market_ticker,
        msg_data={"side": "yes", "price": 47.0, "delta": 5},
        timestamp="1700000100",
    )
    assert result_yes is True
    stored = await fake_redis.hgetall(market_key)
    yes_bids = orjson.loads(stored["yes_bids"])
    assert yes_bids["47.0"] == _TEST_COUNT_5
    assert stored["timestamp"] == "1700000100"
    assert await fake_redis.hget(market_key, "yes_bid") == "47.0"

    result_no = await store._process_orderbook_delta(
        redis=fake_redis,
        market_key=market_key,
        market_ticker=market_ticker,
        msg_data={"side": "no", "price": 42.0, "delta": 3},
        timestamp="1700000200",
    )
    assert result_no is True
    stored_after = await fake_redis.hgetall(market_key)
    yes_asks = orjson.loads(stored_after["yes_asks"])
    assert yes_asks["58.0"] == _TEST_COUNT_3
    assert stored_after["timestamp"] == "1700000200"
    assert await fake_redis.hget(market_key, "yes_ask") == "40.0"
    assert calls[-1] == (market_ticker, 47.0, 40.0)


@pytest.mark.asyncio
async def test_process_orderbook_delta_rejects_unknown_side(store: KalshiStore, fake_redis):
    result = await store._process_orderbook_delta(
        redis=fake_redis,
        market_key=store.get_market_key("TICK-ERR"),
        market_ticker="TICK-ERR",
        msg_data={"side": "maybe", "price": 50, "delta": 1},
        timestamp="1",
    )
    assert result is False


@pytest.mark.asyncio
async def test_update_orderbook_routes_snapshot_and_delta(monkeypatch, store: KalshiStore, fake_redis):
    store.redis = fake_redis
    monkeypatch.setattr(store, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]
    monkeypatch.setattr(store, "_get_redis", AsyncMock(return_value=fake_redis))  # type: ignore[method-assign]
    monkeypatch.setattr("time.time", lambda: 1700000000, raising=False)

    snapshot_message = {
        "type": "orderbook_snapshot",
        "msg": {"market_ticker": "SNAP", "yes": [[50, 1]], "no": [[60, 2]]},
    }
    assert await store.update_orderbook(snapshot_message) is True

    delta_message = {
        "type": "orderbook_delta",
        "msg": {"market_ticker": "SNAP", "side": "yes", "price": 51, "delta": 2},
    }
    assert await store.update_orderbook(delta_message) is True
    assert await fake_redis.hget(store.get_market_key("SNAP"), "yes_bid") == "51.0"

    unsupported = {"type": "unknown", "msg": {"market_ticker": "SNAP"}}
    assert await store.update_orderbook(unsupported) is False


@pytest.mark.asyncio
async def test_update_orderbook_handles_missing_prices(monkeypatch, store: KalshiStore):
    monkeypatch.setattr(store, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]
    monkeypatch.setattr(store, "_get_redis", AsyncMock(return_value=store.redis))  # type: ignore[method-assign]
    monkeypatch.setattr(
        store,
        "_process_orderbook_snapshot",
        AsyncMock(side_effect=RuntimeError("Missing yes_bid_price for illiquid market")),
    )  # type: ignore[method-assign]

    snapshot_message = {
        "type": "orderbook_snapshot",
        "msg": {"market_ticker": "SNAP-LIQ", "yes": [], "no": []},
    }
    assert await store.update_orderbook(snapshot_message) is True


@pytest.mark.asyncio
async def test_update_trade_tick_enriches_prices(monkeypatch, store: KalshiStore, fake_redis):
    store.redis = fake_redis
    monkeypatch.setattr(store, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]
    monkeypatch.setattr(store, "_get_redis", AsyncMock(return_value=fake_redis))  # type: ignore[method-assign]

    message = {
        "msg": {
            "market_ticker": "TRADE-1",
            "side": "yes",
            "price": "45",
            "count": 2,
            "ts": "2024-01-01T12:00:00Z",
            "taker_side": "no",
        }
    }

    assert await store.update_trade_tick(message) is True
    data = await fake_redis.hgetall(store.get_market_key("TRADE-1"))
    assert data["last_trade_side"] == "yes"
    assert data["last_trade_yes_price"] == "45.0"
    assert data["last_trade_no_price"] == "55.0"
    assert data["last_trade_taker_side"] == "no"
    assert data["last_trade_timestamp"].endswith("+00:00")
    assert data["last_price"] == "45.0"


@pytest.mark.asyncio
async def test_update_trade_tick_missing_ticker(monkeypatch, store: KalshiStore):
    monkeypatch.setattr(store, "_ensure_redis_connection", AsyncMock(return_value=True))  # type: ignore[method-assign]
    assert await store.update_trade_tick({"msg": {"side": "yes", "price": "10"}}) is False


@pytest.mark.parametrize(
    "value,expected_suffix",
    [
        ("2024-01-01T00:00:00Z", "+00:00"),
        (1700000000000, "+00:00"),
        ("invalid", ""),
    ],
)
def test_normalise_trade_timestamp_variants(store: KalshiStore, value: object, expected_suffix: str):
    result = store._normalise_trade_timestamp(value)
    if expected_suffix:
        assert result.endswith(expected_suffix)
    else:
        assert result == ""


@pytest.mark.asyncio
async def test_remove_all_kalshi_keys_clears_prefix(store: KalshiStore, fake_redis):
    store.redis = fake_redis
    await fake_redis.set(build_kalshi_market_key("KXBTC-AAA"), "data")
    await fake_redis.set(build_kalshi_market_key("KXBTC-BBB"), "data")
    await fake_redis.set("other:key", "keep")

    assert await store.remove_all_kalshi_keys() is True
    remaining = [key async for key in fake_redis.scan_iter()]
    assert "other:key" in remaining
    assert all(not key.startswith("markets:kalshi") for key in remaining)


@pytest.mark.asyncio
async def test_get_market_metadata_returns_snapshot(store: KalshiStore, fake_redis):
    store.redis = fake_redis
    ticker = "KXTEST-24JAN15-T100"
    market_key = store.get_market_key(ticker)
    metadata = {
        "market_id": "mk-1",
        "status": "trading",
        "yes_bid": "45",
        "yes_ask": "55",
        "timestamp": "1700000000",
    }
    await fake_redis.hset(market_key, mapping=metadata)

    result = await store.get_market_metadata(ticker)
    assert result["market_id"] == "mk-1"
    assert result["status"] == "trading"


@pytest.mark.asyncio
async def test_get_orderbook_handles_invalid_json(store: KalshiStore, fake_redis):
    store.redis = fake_redis
    ticker = "KXTEST-24JAN15-T100"
    market_key = store.get_market_key(ticker)
    await fake_redis.hset(market_key, "yes_bids", "not-json")
    await fake_redis.hset(market_key, "yes_asks", orjson.dumps({"55": 1}).decode())

    orderbook = await store.get_orderbook(ticker)
    assert orderbook["yes_bids"] == {}
    assert orderbook["yes_asks"] == {"55": 1}


@pytest.mark.asyncio
async def test_get_market_field_returns_empty_when_missing(store: KalshiStore, fake_redis):
    store.redis = fake_redis
    ticker = "KXTEST-24JAN15-T100"
    market_key = store.get_market_key(ticker)
    await fake_redis.hset(market_key, "status", "trading")

    value = await store.get_market_field(ticker, "missing")
    assert value == ""


@pytest.mark.asyncio
async def test_close_runs_cleanup_when_loop_active(monkeypatch, connection_store):
    connection_store._pool = object()
    connection_store.redis = SimpleNamespace()

    cleanup_mock = AsyncMock()
    monkeypatch.setattr(kalshi_store_module, "cleanup_redis_pool", cleanup_mock)

    class ActiveLoop:
        def is_closed(self) -> bool:
            return False

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: ActiveLoop())

    await connection_store.close()

    cleanup_mock.assert_awaited_once()
    assert connection_store._pool is None
    assert connection_store.redis is None


@pytest.mark.asyncio
async def test_close_skips_cleanup_when_loop_closed(monkeypatch, connection_store):
    connection_store._pool = object()
    connection_store.redis = SimpleNamespace()

    cleanup_mock = AsyncMock()
    monkeypatch.setattr(kalshi_store_module, "cleanup_redis_pool", cleanup_mock)

    class ClosedLoop:
        def is_closed(self) -> bool:
            return True

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: ClosedLoop())

    await connection_store.close()

    cleanup_mock.assert_not_awaited()
    assert connection_store._pool is None
    assert connection_store.redis is None


@pytest.mark.asyncio
async def test_store_market_metadata_persists_fields(monkeypatch, store: KalshiStore):
    store._ensure_redis_connection = AsyncMock(return_value=True)  # type: ignore[method-assign]

    def fake_extract_time_fields(market_data):
        return {"close_time": "2025-01-01T00:00:00Z"}

    def fake_extract_strike_fields(ticker, strike_type_raw, floor_strike_api, cap_strike_api):
        return {"strike_type": "between", "floor_strike": "0", "cap_strike": "100"}

    def fake_build(
        *,
        market_ticker,
        market_data,
        event_data=None,
        descriptor=None,
        weather_resolver=None,
        logger=None,
    ):
        return {"status": "open", "ticker": market_ticker}

    # Patch validation and build functions in the market_metadata_builder module
    import common.redis_protocol.market_metadata_builder as metadata_builder_module

    monkeypatch.setattr(metadata_builder_module, "_extract_time_fields", fake_extract_time_fields)
    monkeypatch.setattr(metadata_builder_module, "_extract_strike_fields", fake_extract_strike_fields)
    monkeypatch.setattr(metadata_builder_module, "build_market_metadata", fake_build)

    result = await store.store_market_metadata("KXTEST-OPEN", {"status": "open"})
    assert result is True

    market_key = store.get_market_key("KXTEST-OPEN")
    stored = store.redis.dump_hash(market_key)
    assert stored["status"] == "open"
    assert stored["ticker"] == "KXTEST-OPEN"


@pytest.mark.asyncio
async def test_store_market_metadata_requires_connection(monkeypatch, store: KalshiStore):
    store._ensure_redis_connection = AsyncMock(return_value=False)  # type: ignore[method-assign]

    # Patch validation functions so we can test the connection check
    def fake_extract_time_fields(market_data):
        return {"close_time": "2025-01-01T00:00:00Z"}

    def fake_extract_strike_fields(ticker, strike_type_raw, floor_strike_api, cap_strike_api):
        return {"strike_type": "between", "floor_strike": "0", "cap_strike": "100"}

    import common.redis_protocol.market_metadata_builder as metadata_builder_module

    monkeypatch.setattr(metadata_builder_module, "_extract_time_fields", fake_extract_time_fields)
    monkeypatch.setattr(metadata_builder_module, "_extract_strike_fields", fake_extract_strike_fields)

    with pytest.raises(RuntimeError):
        await store.store_market_metadata("KXTEST-FAIL", {"status": "closed"})


@pytest.mark.asyncio
async def test_get_markets_by_currency_filters_records(monkeypatch, fake_redis, schema_config_factory):
    schema_config_factory(kalshi_market_prefix="markets:kalshi")

    logger_instance = logging.getLogger("tests.kalshi_store")
    weather_resolver = WeatherStationResolver(lambda: {}, logger=logger_instance)

    # Use proper __init__ to ensure _attr_resolver and all delegators are initialized
    store = KalshiStore(redis=fake_redis, service_prefix="ws", weather_resolver=weather_resolver)

    # Override specific methods for testing
    async def ensure_connection() -> bool:
        return True

    store._ensure_redis_connection = ensure_connection  # type: ignore[assignment]
    store._find_currency_market_tickers = AsyncMock(return_value=["KXBTC-OPEN-GREATER", "KXBTC-SETTLED"])  # type: ignore[assignment]
    store._market_descriptor = lambda ticker: SimpleNamespace(  # type: ignore[assignment]
        key=build_kalshi_market_key(ticker),
        ticker=ticker,
    )

    monkeypatch.setattr(
        store,
        "_get_redis",
        AsyncMock(return_value=fake_redis),
        raising=False,
    )

    open_metadata = orjson.dumps(
        {
            "status": "open",
            "strike_type": "greater",
            "floor_strike": "30",
            "expected_expiration_time": "2025-01-01T14:00:00+00:00",
        }
    ).decode()
    await fake_redis.hset(
        build_kalshi_market_key("KXBTC-OPEN-GREATER"),
        mapping={
            "metadata": open_metadata,
            "yes_bid": "0.45",
            "yes_ask": "0.55",
        },
    )

    settled_metadata = orjson.dumps(
        {
            "status": "settled",
            "close_time": "2024-01-01T00:00:00+00:00",
            "strike_type": "greater",
            "floor_strike": "20",
        }
    ).decode()
    await fake_redis.hset(
        build_kalshi_market_key("KXBTC-SETTLED"),
        mapping={"metadata": settled_metadata},
    )

    fixed_now = datetime(2024, 12, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "common.time_utils.get_current_utc",
        lambda: fixed_now,
    )

    results = await store.get_markets_by_currency("BTC")
    assert [entry["market_ticker"] for entry in results] == ["KXBTC-OPEN-GREATER"]
    assert results[0]["expiry"] == "2025-01-01T14:00:00+00:00"
    assert results[0]["strike"] == _VAL_30_0
    store.logger.debug.assert_called()


@pytest.mark.asyncio
async def test_get_active_strikes_and_expiries_groups_strikes(monkeypatch, connection_store):
    connection_store.logger = Mock(spec=logging.Logger)
    markets = [
        {
            "expiry": "2025-01-01T14:00:00+00:00",
            "strike": "30",
            "strike_type": "greater",
            "market_ticker": "KXBTC-OPEN",
            "floor_strike": "30",
            "cap_strike": "",
            "event_type": "temperature",
            "event_ticker": "EVT",
        }
    ]
    monkeypatch.setattr(
        connection_store,
        "get_markets_by_currency",
        AsyncMock(return_value=markets),
        raising=False,
    )

    summary = await connection_store.get_active_strikes_and_expiries("BTC")
    assert list(summary.keys()) == ["2025-01-01T14:00:00+00:00"]
    entry = summary["2025-01-01T14:00:00+00:00"][0]
    assert entry["market_tickers"] == ["KXBTC-OPEN"]
    connection_store.logger.debug.assert_called()


@pytest.mark.asyncio
async def test_get_active_strikes_and_expiries_requires_markets(monkeypatch, connection_store):
    connection_store.logger = Mock(spec=logging.Logger)
    monkeypatch.setattr(
        connection_store,
        "get_markets_by_currency",
        AsyncMock(return_value=[]),
        raising=False,
    )

    with pytest.raises(KalshiStoreError, match="No active Kalshi markets"):
        await connection_store.get_active_strikes_and_expiries("BTC")


@pytest.mark.asyncio
async def test_get_interpolation_results_filters_currency(monkeypatch, fake_redis):
    module_logger = Mock(spec=logging.Logger)
    monkeypatch.setattr(kalshi_store_module, "logger", module_logger)

    weather_resolver = WeatherStationResolver(lambda: {}, logger=module_logger)

    # Use proper __init__ to ensure _attr_resolver and all delegators are initialized
    store = KalshiStore(redis=fake_redis, service_prefix="ws", weather_resolver=weather_resolver)

    # Override specific methods for testing
    async def ensure_connection() -> bool:
        return True

    store._ensure_redis_connection = ensure_connection  # type: ignore[assignment]
    store._get_redis = AsyncMock(return_value=fake_redis)  # type: ignore[assignment]
    store._scan_market_keys = AsyncMock(  # type: ignore[assignment]
        return_value=[
            build_kalshi_market_key("KXBTC-M1"),
            build_kalshi_market_key("KXBTC-BAD"),
            build_kalshi_market_key("KXETH-M2"),
        ]
    )

    def fake_parse(key: str):
        return SimpleNamespace(ticker=key.split(":")[-1])

    monkeypatch.setattr(kalshi_store_module, "parse_kalshi_market_key", fake_parse)

    await fake_redis.hset(
        build_kalshi_market_key("KXBTC-M1"),
        mapping={
            "t_yes_bid": "0.25",
            "t_yes_ask": "0.30",
            "interpolation_method": "fast",
            "deribit_points_used": "5",
            "interpolation_quality_score": "0.8",
            "interpolation_timestamp": "2024-01-01T00:00:00Z",
            "interp_error_bid": "0.01",
            "interp_error_ask": "0.02",
        },
    )

    await fake_redis.hset(
        build_kalshi_market_key("KXBTC-BAD"),
        mapping={
            "t_yes_bid": "not-a-number",
            "interpolation_method": "bad",
            "deribit_points_used": "foo",
        },
    )

    await fake_redis.hset(
        build_kalshi_market_key("KXETH-M2"),
        mapping={
            "t_yes_bid": "0.5",
            "t_yes_ask": "0.6",
        },
    )

    results = await store.get_interpolation_results("BTC")
    assert list(results.keys()) == ["KXBTC-M1"]
    payload = results["KXBTC-M1"]
    assert payload["t_yes_bid"] == _VAL_0_25
    assert payload["t_yes_ask"] == _VAL_0_3
    assert payload["deribit_points_used"] == _TEST_COUNT_5
    module_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_get_market_data_for_strike_expiry_returns_match(monkeypatch, store: KalshiStore, fake_redis):
    store.redis = fake_redis
    store._initialized = True
    store._ensure_redis_connection = AsyncMock(return_value=True)  # type: ignore[method-assign]
    monkeypatch.setattr(
        store,
        "get_subscribed_markets",
        AsyncMock(return_value={"KXBTC-20250101-KNYC-G30"}),
        raising=False,
    )

    market_ticker = "KXBTC-20250101-KNYC-G30"
    market_key = store.get_market_key(market_ticker)
    metadata = orjson.dumps(
        {
            "close_time": "2025-01-01T12:00:00+00:00",
            "strike_type": "greater",
            "floor_strike": "30",
            "yes_bid": "0.45",
            "yes_ask": "0.55",
        }
    ).decode()
    orderbook = orjson.dumps(
        {
            "yes_bids": {"0.45": 10},
            "yes_asks": {"0.55": 8},
        }
    ).decode()

    await fake_redis.hset(
        market_key,
        mapping={
            "metadata": metadata,
            "orderbook": orderbook,
        },
    )

    result = await store.get_market_data_for_strike_expiry(
        "BTC",
        "2025-01-01T12:00:00+00:00",
        30.0,
    )

    assert result["market_ticker"] == market_ticker
    assert result["best_bid"] == _VAL_0_45
    assert result["best_bid_size"] == _TEST_COUNT_10
    assert result["best_ask"] == _VAL_0_55
    assert result["best_ask_size"] == _TEST_COUNT_8


@pytest.mark.asyncio
async def test_is_market_expired_detects_close_time(monkeypatch, store: KalshiStore, fake_redis):
    store.redis = fake_redis
    store._initialized = True
    store._ensure_redis_connection = AsyncMock(return_value=True)  # type: ignore[method-assign]
    market_ticker = "KXBTC-20240101-KNYC-G30"
    market_key = store.get_market_key(market_ticker)
    await fake_redis.hset(
        market_key,
        mapping={"close_time": "2024-01-01T00:00:00+00:00"},
    )

    monkeypatch.setattr(
        "common.time_utils.get_current_utc",
        lambda: datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    assert await store.is_market_expired(market_ticker) is True
