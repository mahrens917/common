import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import orjson
import pytest

from common.redis_protocol import kalshi_store as kalshi_store_module
from common.redis_protocol.kalshi_store import KalshiStore
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

_CONST_2024 = 2024
_TEST_ID_123 = 123
_VAL_7_0 = 7.0

from common.redis_protocol.weather_station_resolver import WeatherStationResolver
from common.redis_schema import KalshiMarketDescriptor


@pytest.fixture(autouse=True)
def _stub_schema(schema_config_factory):
    """Ensure the KalshiStore module uses the deterministic schema for tests."""

    config = schema_config_factory(kalshi_market_prefix="markets:kalshi")
    kalshi_store_module.SCHEMA = config  # type: ignore[assignment]
    return config


@pytest.fixture
def store(monkeypatch, fake_redis):
    """Return a fully initialised KalshiStore backed by the in-memory FakeRedis."""

    async def ensure(self):
        self.redis = fake_redis
        self._initialized = True
        return True

    async def get_redis(self):
        await ensure(self)
        return fake_redis

    monkeypatch.setattr(KalshiStore, "_ensure_redis_connection", ensure, raising=False)
    monkeypatch.setattr(KalshiStore, "_get_redis", get_redis, raising=False)

    async def _scan(self, cursor: int, match: str | None = None, count: int | None = None):
        collected = []
        async for key in self.scan_iter(match, count=count):
            collected.append(key)
        return 0, collected

    fake_redis.scan = _scan.__get__(fake_redis, fake_redis.__class__)  # type: ignore[attr-defined]

    resolver = WeatherStationResolver(
        lambda: {
            "TEST": {"icao": "KTEST", "aliases": ["ALTT"]},
            "ALTT": {"icao": "KALT", "aliases": []},
        },
        logger=logging.getLogger("tests.kalshi_store_full"),
    )
    store_obj = KalshiStore(redis=fake_redis, service_prefix="ws", weather_resolver=resolver)
    store_obj.redis = fake_redis
    store_obj._initialized = True
    return store_obj, fake_redis


def test_convert_numeric_field_edge_cases():
    assert convert_numeric_field(None) is None
    assert convert_numeric_field("") is None
    assert convert_numeric_field("  ") is None
    assert convert_numeric_field("3.5") == pytest.approx(3.5)
    assert convert_numeric_field(7) == _VAL_7_0
    assert convert_numeric_field(3.14) == pytest.approx(3.14)
    with pytest.raises(ValueError):
        convert_numeric_field("invalid")
    with pytest.raises(ValueError):
        convert_numeric_field({"a": 1})


def test_normalise_hash_and_top_of_book_alignment():
    yes_bids = orjson.dumps({"40": 2})
    yes_asks = orjson.dumps({"45": 3})
    raw: Dict[Any, Any] = {b"yes_bids": yes_bids, "yes_asks": yes_asks}
    normalized = normalise_hash(raw)
    assert normalized == {"yes_bids": yes_bids.decode(), "yes_asks": yes_asks.decode()}

    snapshot = {"yes_bids": normalized["yes_bids"], "yes_asks": normalized["yes_asks"]}
    sync_top_of_book_fields(snapshot)
    assert snapshot["yes_bid"] == "40.0"
    assert snapshot["yes_bid_size"] == "2"
    assert snapshot["yes_ask"] == "45.0"
    assert snapshot["yes_ask_size"] == "3"


@pytest.mark.asyncio
async def test_store_optional_field_handles_none(monkeypatch, fake_redis):
    store_obj = KalshiStore(redis=fake_redis)
    store_obj.redis = fake_redis
    await store_obj._store_optional_field(fake_redis, "hash", "field", None)
    await store_obj._store_optional_field(fake_redis, "hash", "field", 12)
    data = await fake_redis.hgetall("hash")
    assert data["field"] == "12"


def test_format_probability_value_strips_trailing_zeroes():
    assert format_probability_value("0.1234500000") == "0.12345"
    with pytest.raises(ValueError):
        format_probability_value("nan")
    with pytest.raises(ValueError):
        format_probability_value("not-a-number")


def test_weather_station_mapping_helpers(store):
    store_obj, _ = store
    resolver = store_obj.weather_resolver
    assert resolver.extract_station("KXHIGHTEST-24JAN01-T100") == "KTEST"
    assert resolver.extract_station("KXHIGHALTT-24JAN01-T100") == "KALT"
    assert resolver.extract_station("KXOTHER-24JAN01-T100") is None
    assert resolver.resolve_city_alias("ALTT") == "TEST"
    assert resolver.resolve_city_alias("UNKNOWN") is None


def test_parse_expiry_token_variants(store):
    parsed = parse_expiry_token("24JAN15")
    assert parsed.year == _CONST_2024 and parsed.month == 1

    future = parse_expiry_token("15JAN1530")
    assert isinstance(future, datetime)
    assert future.tzinfo == timezone.utc

    assert parse_expiry_token("  ") is None
    assert parse_expiry_token("15XYZ30") is None


def test_derive_expiry_iso_requires_valid_sources(store):
    store_obj, _ = store
    # Metadata already contains close_time
    metadata = {"close_time": "2024-02-01T00:00:00+00:00"}
    descriptor = store_obj._market_descriptor("KXBTC-TEST")
    assert (
        derive_expiry_iso(
            "KXBTC-TEST",
            metadata,
            descriptor=descriptor,
            token_parser=parse_expiry_token,
        )
        == "2024-02-01T00:00:00+00:00"
    )

    # No close_time but ticker contains tokens that resolve
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    metadata = {"timestamp": str(future.timestamp())}
    descriptor = store_obj._market_descriptor("KXBTCAAA-24JAN15-T100")
    iso = derive_expiry_iso(
        "KXBTCAAA-24JAN15-T100",
        metadata,
        descriptor=descriptor,
        token_parser=parse_expiry_token,
    )
    assert iso.endswith("+00:00")

    descriptor = store_obj._market_descriptor("UNKNOWN")
    with pytest.raises(RuntimeError):
        derive_expiry_iso(
            "UNKNOWN",
            {},
            descriptor=descriptor,
            token_parser=parse_expiry_token,
            now=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )


def test_derive_strike_fields():
    assert derive_strike_fields("KXBTC-XYZ-T100") == ("greater", 100.0, None, 100.0)
    assert derive_strike_fields("KXBTC-XYZ-B50") == ("less", None, 50.0, 50.0)
    assert derive_strike_fields("KXBTC-XYZ-M75") == ("between", None, None, 75.0)
    assert derive_strike_fields("KXHIGH-20240101-KNYC-BETWEEN-70-90") == (
        "between",
        70.0,
        90.0,
        90.0,
    )
    assert derive_strike_fields("KXBTC-XYZ") is None


def test_ensure_market_metadata_fields_enriches_snapshot(store):
    store_obj, _ = store
    metadata = {
        "timestamp": str(datetime.now(timezone.utc).timestamp()),
        "status": "trading",
        "yes_bids": "{}",
    }
    descriptor = store_obj._market_descriptor("KXBTCTEST-T100")
    enriched = ensure_market_metadata_fields(
        "KXBTCTEST-T100",
        metadata,
        descriptor=descriptor,
        token_parser=parse_expiry_token,
    )
    assert enriched["ticker"] == "KXBTCTEST-T100"
    assert enriched["strike_type"] == "greater"
    assert enriched["floor_strike"] == "100.0"
    assert enriched["status"] == "trading"
    assert enriched["yes_asks"] == "{}"


def test_select_and_normalize_timestamp():
    data = {"ts": 0, "supplemental": 123}
    assert select_timestamp_value(data, ["missing", "ts", "supplemental"]) == _TEST_ID_123

    iso = normalize_timestamp("2024-01-01T00:00:00Z")
    assert iso == "2024-01-01T00:00:00+00:00"
    unix = normalize_timestamp(1704067200)
    assert unix.startswith("2023") or unix.startswith("2024")
    assert normalize_timestamp("") is None


@pytest.mark.asyncio
async def test_get_redis_handles_reinitialization(monkeypatch, fake_redis):
    store_obj = KalshiStore(service_prefix="ws")
    store_obj.redis = fake_redis
    store_obj._initialized = False

    called = {"ensure": 0}

    async def ensure(self):
        called["ensure"] += 1
        self.redis = fake_redis
        self._initialized = True
        return True

    monkeypatch.setattr(KalshiStore, "_ensure_redis_connection", ensure, raising=False)
    result = await store_obj._get_redis()
    assert result is fake_redis
    assert called["ensure"] == 1


@pytest.mark.asyncio
async def test_ensure_redis_connection_recreates_client(monkeypatch):
    ping_calls = {"count": 0}

    class Pingable:
        def __init__(self):
            self.closed = False
            self.connection_pool = None

        async def ping(self):
            ping_calls["count"] += 1
            return True

    async def fake_get_redis_client():
        return Pingable()

    monkeypatch.setattr("common.redis_protocol.connection_pool_core.get_redis_client", fake_get_redis_client)

    store_obj = KalshiStore()
    assert await store_obj._ensure_redis_connection() is True
    assert ping_calls["count"] == 1


@pytest.mark.asyncio
async def test_store_and_fetch_market_metadata_cycle(store):
    """Test metadata store/fetch cycle.

    Note: store_market_metadata only stores Kalshi API metadata fields.
    Price fields like yes_bid are derived from orderbook (yes_bids) during snapshot retrieval.
    """
    store_obj, redis_client = store
    ticker = "KXHIGHTEST-24JAN15-T100"
    market_data = {
        "id": "mkt-1",
        "close_time": "",
        "strike_type": "greater",
        "floor_strike": 100,
        "yes_bids": {"45": 2},
        "yes_asks": {"55": 1},
    }
    await store_obj.store_market_metadata(ticker, market_data, event_data={"title": "Event"})

    # Store orderbook as JSON (how it would be stored in production)
    # yes_bid/yes_ask are derived from yes_bids/yes_asks during sync_top_of_book_fields
    market_key = store_obj.get_market_key(ticker)
    await redis_client.hset(
        market_key,
        mapping={
            "yes_bids": orjson.dumps({"45": 2}).decode(),
            "yes_asks": orjson.dumps({"55": 1}).decode(),
        },
    )

    snapshot = await store_obj.get_market_snapshot(ticker)
    assert snapshot["market_id"] == "mkt-1"
    # yes_bid is derived from yes_bids orderbook (best bid price = 45)
    assert snapshot["yes_bid"] == "45.0"
    assert snapshot["event_title"] == "Event"

    data = await store_obj.get_market_metadata(ticker)
    assert data["market_id"] == "mkt-1"

    orderbook = await store_obj.get_orderbook(ticker)
    assert orderbook["yes_bids"] == {"45": 2}
    # Note: yes_bid is derived during snapshot retrieval, not stored directly
    # So we verify it through the snapshot, not get_market_field
    side = await store_obj.get_orderbook_side(ticker, "yes_bids")
    assert side == {"45": 2}


@pytest.mark.asyncio
async def test_subscriptions_and_service_status(store):
    store_obj, _ = store
    await store_obj.add_subscribed_market("AAA")
    await store_obj.add_subscribed_market("BBB")
    assert await store_obj.get_subscribed_markets() == {"AAA", "BBB"}
    await store_obj.remove_subscribed_market("AAA")
    assert await store_obj.get_subscribed_markets() == {"BBB"}

    await store_obj.record_subscription_ids({"AAA": 1, "BBB": 2})
    ids = await store_obj.fetch_subscription_ids(market_tickers=["AAA", "BBB", "CCC"])
    assert ids == {"AAA": "1", "BBB": "2"}
    await store_obj.clear_subscription_ids(market_tickers=["AAA", "BBB"])
    assert await store_obj.fetch_subscription_ids(market_tickers=["AAA"]) == {}

    await store_obj.update_service_status("collector", {"status": "running"})
    assert await store_obj.get_service_status("collector") == "running"


@pytest.mark.asyncio
async def test_market_filters_and_queries(store):
    store_obj, redis_client = store
    ticker = "KXBTC-USD-24JAN15-T100"
    key = store_obj.get_market_key(ticker)
    future_close = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    market_payload = {
        "id": "btc-1",
        "status": "open",
        "close_time": future_close,
        "strike_type": "greater",
        "floor_strike": 100,
        "yes_bid": 45,
        "yes_ask": 55,
        "yes_bids": {"45": 2},
        "yes_asks": {"55": 1},
        "orderbook": orjson.dumps({"yes_bids": {"45": 2}, "yes_asks": {"55": 1}}).decode(),
    }
    await store_obj.store_market_metadata(ticker, market_payload)
    await redis_client.hset(key, "metadata", orjson.dumps(market_payload).decode())
    await redis_client.hset(
        key,
        mapping={"orderbook": orjson.dumps({"yes_bids": {"45": 2}, "yes_asks": {"55": 1}}).decode()},
    )
    await store_obj.add_subscribed_market(ticker)
    await store_obj.record_subscription_ids({ticker: "abc"})

    assert bool(await store_obj.is_market_tracked(ticker)) is True

    markets = await store_obj.get_markets_by_currency("btc")
    assert markets and markets[0]["ticker"] == ticker

    strikes = await store_obj.get_active_strikes_and_expiries("btc")
    assert strikes

    expiry = next(iter(strikes))
    strike_value = strikes[expiry][0]["strike"]
    market_info = await store_obj.get_market_data_for_strike_expiry("btc", expiry, strike_value)
    assert market_info is not None

    await redis_client.hset(key, mapping={"close_time": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()})
    assert await store_obj.is_market_settled(ticker) is True

    await redis_client.hset(key, mapping={"close_time": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()})
    assert await store_obj.is_market_expired(ticker) is True


@pytest.mark.asyncio
async def test_market_removals_and_service_cleanup(store):
    store_obj, redis_client = store
    ticker = "KXHIGHTEST-24JAN15-T100"
    key = store_obj.get_market_key(ticker)
    await redis_client.hset(key, mapping={"ticker": ticker})
    await store_obj.add_subscribed_market(ticker)
    await store_obj.record_subscription_ids({ticker: "123"})

    assert await store_obj.remove_market_completely(ticker) is True
    assert await redis_client.hgetall(key) == {}

    await redis_client.set("kalshi:ws:test", "value")
    await redis_client.hset(store_obj.SUBSCRIPTIONS_KEY, mapping={"ws:test": "1", "rest:keep": "1"})
    assert await store_obj.remove_service_keys() is True
    assert await redis_client.get("kalshi:ws:test") is None

    await redis_client.hset("markets:kalshi:binary:KEEP", mapping={"a": 1})
    await redis_client.hset("markets:kalshi:binary:REMOVE", mapping={"a": 1})
    assert await store_obj.clear_market_metadata(pattern="markets:kalshi:binary:*") >= 1

    await redis_client.hset(key, mapping={"ticker": ticker})
    assert await store_obj.remove_all_kalshi_keys() is True


@pytest.mark.asyncio
async def test_write_enhanced_market_data_and_snapshots(store):
    store_obj, redis_client = store
    ticker = "KXHIGHTEST-24JAN15-T100"
    key = store_obj.get_market_key(ticker)
    await redis_client.hset(key, mapping={"ticker": ticker})

    await store_obj.write_enhanced_market_data(ticker, {"prob_yes": 0.42})
    data = await redis_client.hgetall(key)
    assert data["prob_yes"] == "0.42"

    snapshot = await store_obj.get_market_snapshot_by_key(key)
    assert snapshot["ticker"] == ticker


@pytest.mark.asyncio
async def test_interpolation_results_flow(store):
    store_obj, redis_client = store
    ticker = "KXBTC-USD-24JAN15-T100"
    key = store_obj.get_market_key(ticker)
    await redis_client.hset(key, mapping={"ticker": ticker})

    await store_obj.update_interpolation_results(
        "btc",
        {
            ticker: {
                "t_yes_bid": 0.1,
                "t_yes_ask": 0.2,
                "interpolation_method": "linear",
                "deribit_points_used": 2,
                "interpolation_quality_score": 0.95,
                "interp_error_bid": 0.01,
                "interp_error_ask": 0.02,
            }
        },
    )
    stored = await store_obj.get_interpolation_results("btc")
    assert stored[ticker]["t_yes_bid"] == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_orderbook_and_trade_updates(store):
    store_obj, redis_client = store
    ticker = "KXHIGHTEST-24JAN15-T100"

    message = {
        "type": "orderbook_snapshot",
        "msg": {
            "market_ticker": ticker,
            "yes": [[42, 2]],
            "no": [[58, 1]],
        },
    }
    assert await store_obj.update_orderbook(message) is True
    orderbook = await redis_client.hgetall(store_obj.get_market_key(ticker))
    assert orjson.loads(orderbook["yes_bids"]) == {"42": 2}

    trade_message = {
        "msg": {
            "market_ticker": ticker,
            "side": "yes",
            "price": 44.5,
            "quantity": 3,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    }
    assert await store_obj.update_trade_tick(trade_message) is True
    market_data = await redis_client.hgetall(store_obj.get_market_key(ticker))
    assert market_data["last_trade_yes_price"] == "44.5"

    timestamp = kalshi_store_module.KalshiStore._normalise_trade_timestamp(trade_message["msg"]["ts"])
    assert timestamp.endswith("+00:00")


def test_market_descriptor_accessors(store):
    store_obj, _ = store
    assert store_obj.SUBSCRIPTIONS_KEY == "kalshi:subscriptions"
    assert store_obj.SERVICE_STATUS_KEY == "status"
    assert store_obj.SUBSCRIBED_MARKETS_KEY == "kalshi:subscribed_markets"
    assert store_obj.SUBSCRIPTION_IDS_KEY == "kalshi:subscription_ids:ws"

    descriptor = store_obj._market_descriptor("KXBTC-USD-24JAN15-T100")
    assert isinstance(descriptor, KalshiMarketDescriptor)
    assert store_obj.get_market_key("KXBTC-USD-24JAN15-T100") == descriptor.key


@pytest.mark.asyncio
async def test_pipeline_trade_price_updates(store, monkeypatch):
    store_obj, _ = store
    ticker = "KXHIGHTEST-24JAN15-T100"
    calls = []

    class FakeTradeStore:
        async def update_trade_prices(self, market_ticker, yes_bid, yes_ask):
            calls.append((market_ticker, yes_bid, yes_ask))

    monkeypatch.setattr("common.redis_protocol.trade_store.TradeStore", FakeTradeStore, raising=False)

    await store_obj._update_trade_prices_for_market(ticker, 41, 59)
    assert calls == [(ticker, 41, 59)]

    # Ensure missing prices short-circuit
    await store_obj._update_trade_prices_for_market(ticker, None, 59)
    assert calls == [(ticker, 41, 59)]


@pytest.mark.asyncio
async def test_initialize_and_close(monkeypatch):
    fake_pool = object()

    class DummyRedis:
        def __init__(self, **kwargs):
            pass

        async def ping(self):
            return True

        async def close(self):
            return None

    async def fake_get_pool():
        return fake_pool

    async def fake_cleanup(pool):
        assert pool is fake_pool

    monkeypatch.setattr("common.redis_protocol.kalshi_store.Redis", DummyRedis, raising=False)
    monkeypatch.setattr("common.redis_protocol.connection.get_redis_pool", fake_get_pool, raising=False)
    monkeypatch.setattr("common.redis_protocol.connection.cleanup_redis_pool", fake_cleanup, raising=False)

    store_obj = KalshiStore()
    assert await store_obj.initialize() is True
    await store_obj.close()
