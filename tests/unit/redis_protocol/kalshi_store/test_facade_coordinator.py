"""Tests for facade_coordinator module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.facade_coordinator import (
    ConnectionDelegator,
    MarketQueryDelegator,
    MetadataDelegator,
    SubscriptionDelegator,
)


@pytest.fixture
def connection_manager():
    """Create mock connection manager."""
    mgr = MagicMock()
    mgr.get_redis = AsyncMock(return_value=MagicMock())
    mgr.reset_connection_state = MagicMock()
    mgr.close_redis_client = AsyncMock()
    mgr.resolve_connection_settings = MagicMock(return_value={"host": "localhost"})
    mgr.acquire_pool = AsyncMock(return_value=MagicMock())
    mgr.create_redis_client = AsyncMock(return_value=MagicMock())
    mgr.verify_connection = AsyncMock(return_value=(True, True))
    mgr.ping_connection = AsyncMock(return_value=(True, True))
    mgr.connect_with_retry = AsyncMock(return_value=True)
    mgr.ensure_redis_connection = AsyncMock(return_value=True)
    return mgr


@pytest.fixture
def reader():
    """Create mock reader."""
    r = MagicMock()
    r.get_markets_by_currency = AsyncMock(return_value=[{"ticker": "TEST"}])
    r.get_active_strikes_and_expiries = AsyncMock(return_value={"strikes": []})
    r.get_market_data_for_strike_expiry = AsyncMock(return_value={"data": True})
    r.get_subscribed_markets = AsyncMock(return_value={"TEST"})
    r.is_market_tracked = AsyncMock(return_value=True)
    return r


@pytest.fixture
def writer():
    """Create mock writer."""
    w = MagicMock()
    w.subscribe_to_market = AsyncMock(return_value=True)
    w.unsubscribe_from_market = AsyncMock(return_value=True)
    w.store_market_metadata = AsyncMock(return_value=True)
    return w


@pytest.fixture
def metadata_adapter():
    """Create mock metadata adapter."""
    m = MagicMock()
    m.weather_resolver = None
    return m


@pytest.fixture
def subscription_tracker():
    """Create mock subscription tracker."""
    s = MagicMock()
    s.SUBSCRIPTIONS_KEY = "subscriptions"
    s.SERVICE_STATUS_KEY = "status"
    s.SUBSCRIBED_MARKETS_KEY = "markets"
    s.SUBSCRIPTION_IDS_KEY = "ids"
    s.add_subscribed_market = AsyncMock(return_value=True)
    s.remove_subscribed_market = AsyncMock(return_value=True)
    s.record_subscription_ids = AsyncMock()
    s.fetch_subscription_ids = AsyncMock(return_value=[])
    s.clear_subscription_ids = AsyncMock()
    s.update_service_status = AsyncMock(return_value=True)
    s.get_service_status = AsyncMock(return_value="active")
    return s


@pytest.mark.asyncio
async def test_connection_delegator_get_redis(connection_manager):
    """Test ConnectionDelegator.get_redis."""
    delegator = ConnectionDelegator(connection_manager)
    redis = await delegator.get_redis()
    assert redis is not None
    connection_manager.get_redis.assert_awaited_once()


def test_connection_delegator_reset_connection_state(connection_manager):
    """Test ConnectionDelegator.reset_connection_state."""
    delegator = ConnectionDelegator(connection_manager)
    delegator.reset_connection_state()
    connection_manager.reset_connection_state.assert_called_once()


@pytest.mark.asyncio
async def test_connection_delegator_close_redis_client(connection_manager):
    """Test ConnectionDelegator.close_redis_client."""
    delegator = ConnectionDelegator(connection_manager)
    client = MagicMock()
    await delegator.close_redis_client(client)
    connection_manager.close_redis_client.assert_awaited_once_with(client)


def test_connection_delegator_resolve_connection_settings(connection_manager):
    """Test ConnectionDelegator.resolve_connection_settings."""
    delegator = ConnectionDelegator(connection_manager)
    settings = delegator.resolve_connection_settings()
    assert settings == {"host": "localhost"}


@pytest.mark.asyncio
async def test_connection_delegator_create_redis_client(connection_manager):
    """Test ConnectionDelegator.create_redis_client."""
    delegator = ConnectionDelegator(connection_manager)
    client = await delegator.create_redis_client()
    assert client is not None
    connection_manager.create_redis_client.assert_awaited_once()


@pytest.mark.asyncio
async def test_connection_delegator_verify_connection(connection_manager):
    """Test ConnectionDelegator.verify_connection."""
    delegator = ConnectionDelegator(connection_manager)
    redis = MagicMock()
    result = await delegator.verify_connection(redis)
    assert result == (True, True)
    connection_manager.verify_connection.assert_awaited_once_with(redis)


@pytest.mark.asyncio
async def test_connection_delegator_ping_connection(connection_manager):
    """Test ConnectionDelegator.ping_connection."""
    delegator = ConnectionDelegator(connection_manager)
    redis = MagicMock()
    result = await delegator.ping_connection(redis, timeout=10.0)
    assert result == (True, True)
    connection_manager.ping_connection.assert_awaited_once_with(redis, timeout=10.0)


@pytest.mark.asyncio
async def test_connection_delegator_connect_with_retry(connection_manager):
    """Test ConnectionDelegator.connect_with_retry."""
    delegator = ConnectionDelegator(connection_manager)
    result = await delegator.connect_with_retry(allow_reuse=False, context="test", attempts=5, retry_delay=0.2)
    assert result is True
    connection_manager.connect_with_retry.assert_awaited_once()


@pytest.mark.asyncio
async def test_connection_delegator_ensure_redis_connection(connection_manager):
    """Test ConnectionDelegator.ensure_redis_connection."""
    delegator = ConnectionDelegator(connection_manager)
    result = await delegator.ensure_redis_connection()
    assert result is True
    connection_manager.ensure_redis_connection.assert_awaited_once()


def test_metadata_delegator_build_kalshi_metadata(writer, reader, metadata_adapter):
    """Test MetadataDelegator.build_kalshi_metadata."""
    # Setup writer with metadata_writer
    metadata_writer = MagicMock()
    metadata_writer._build_kalshi_metadata = MagicMock(return_value={"meta": True})
    writer._metadata_writer = metadata_writer
    writer._metadata = metadata_adapter

    delegator = MetadataDelegator(writer, reader, None)
    result = delegator.build_kalshi_metadata("KXHIGHTEST-24JAN01-T1.50", {})
    assert result == {"meta": True}
    metadata_writer._build_kalshi_metadata.assert_called_once()


def test_metadata_delegator_extract_weather_station_from_ticker(writer, reader):
    """Test MetadataDelegator.extract_weather_station_from_ticker."""
    weather_resolver = MagicMock(return_value="STATION1")
    delegator = MetadataDelegator(writer, reader, lambda: weather_resolver)
    result = delegator.extract_weather_station_from_ticker("WEATHER-TICKER")
    assert result is not None


def test_metadata_delegator_extract_weather_station_no_resolver(writer, reader):
    """Test MetadataDelegator.extract_weather_station_from_ticker without resolver."""
    writer._metadata = MagicMock()
    writer._metadata.weather_resolver = None
    delegator = MetadataDelegator(writer, reader, None)
    result = delegator.extract_weather_station_from_ticker("WEATHER-TICKER")
    assert result is None


def test_metadata_delegator_derive_expiry_iso(writer, reader):
    """Test MetadataDelegator.derive_expiry_iso."""
    writer.derive_expiry_iso = MagicMock(return_value="2024-01-01")
    delegator = MetadataDelegator(writer, reader, None)
    result = delegator.derive_expiry_iso("KXHIGHTEST-24JAN01-T1.50", {})
    assert result == "2024-01-01"
    writer.derive_expiry_iso.assert_called_once()


def test_metadata_delegator_ensure_market_metadata_fields(writer, reader):
    """Test MetadataDelegator.ensure_market_metadata_fields."""
    reader.ensure_market_metadata_fields = MagicMock(return_value={"fields": True})
    delegator = MetadataDelegator(writer, reader, None)
    result = delegator.ensure_market_metadata_fields("TEST", {})
    assert result == {"fields": True}
    reader.ensure_market_metadata_fields.assert_called_once()


def test_subscription_delegator_properties(subscription_tracker):
    """Test SubscriptionDelegator property accessors."""
    delegator = SubscriptionDelegator(subscription_tracker)
    assert delegator.SUBSCRIPTIONS_KEY == "subscriptions"
    assert delegator.SERVICE_STATUS_KEY == "status"
    assert delegator.SUBSCRIBED_MARKETS_KEY == "markets"
    assert delegator.SUBSCRIPTION_IDS_KEY == "ids"


@pytest.mark.asyncio
async def test_subscription_delegator_add_subscribed_market(subscription_tracker):
    """Test SubscriptionDelegator.add_subscribed_market."""
    delegator = SubscriptionDelegator(subscription_tracker)
    result = await delegator.add_subscribed_market("TEST", category="crypto")
    assert result is True
    subscription_tracker.add_subscribed_market.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_delegator_remove_subscribed_market(subscription_tracker):
    """Test SubscriptionDelegator.remove_subscribed_market."""
    delegator = SubscriptionDelegator(subscription_tracker)
    result = await delegator.remove_subscribed_market("TEST", category="crypto")
    assert result is True
    subscription_tracker.remove_subscribed_market.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_delegator_record_subscription_ids(subscription_tracker):
    """Test SubscriptionDelegator.record_subscription_ids."""
    delegator = SubscriptionDelegator(subscription_tracker)
    await delegator.record_subscription_ids("service", ["id1", "id2"], expiry=3600)
    subscription_tracker.record_subscription_ids.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_delegator_fetch_subscription_ids(subscription_tracker):
    """Test SubscriptionDelegator.fetch_subscription_ids."""
    delegator = SubscriptionDelegator(subscription_tracker)
    result = await delegator.fetch_subscription_ids("service", expiry=3600)
    assert result == []
    subscription_tracker.fetch_subscription_ids.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_delegator_clear_subscription_ids(subscription_tracker):
    """Test SubscriptionDelegator.clear_subscription_ids."""
    delegator = SubscriptionDelegator(subscription_tracker)
    await delegator.clear_subscription_ids("service")
    subscription_tracker.clear_subscription_ids.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_delegator_update_service_status(subscription_tracker):
    """Test SubscriptionDelegator.update_service_status."""
    delegator = SubscriptionDelegator(subscription_tracker)
    result = await delegator.update_service_status("service", {"status": "ok"})
    assert result is True
    subscription_tracker.update_service_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_delegator_get_service_status(subscription_tracker):
    """Test SubscriptionDelegator.get_service_status."""
    delegator = SubscriptionDelegator(subscription_tracker)
    result = await delegator.get_service_status("service")
    assert result == "active"
    subscription_tracker.get_service_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_market_query_delegator_get_markets_by_currency(reader):
    """Test MarketQueryDelegator.get_markets_by_currency."""
    delegator = MarketQueryDelegator(reader)
    result = await delegator.get_markets_by_currency("USD")
    assert result == [{"ticker": "TEST"}]
    reader.get_markets_by_currency.assert_awaited_once_with("USD")


@pytest.mark.asyncio
async def test_market_query_delegator_get_active_strikes_and_expiries(reader):
    """Test MarketQueryDelegator.get_active_strikes_and_expiries."""
    delegator = MarketQueryDelegator(reader)
    result = await delegator.get_active_strikes_and_expiries("USD")
    assert result == {"strikes": []}
    reader.get_active_strikes_and_expiries.assert_awaited_once_with("USD")


@pytest.mark.asyncio
async def test_market_query_delegator_get_market_data_for_strike_expiry(reader):
    """Test MarketQueryDelegator.get_market_data_for_strike_expiry."""
    delegator = MarketQueryDelegator(reader)
    result = await delegator.get_market_data_for_strike_expiry("USD", "2024-01-01", 100.0)
    assert result == {"data": True}
    reader.get_market_data_for_strike_expiry.assert_awaited_once()


@pytest.mark.asyncio
async def test_market_query_delegator_get_subscribed_markets(reader):
    """Test MarketQueryDelegator.get_subscribed_markets."""
    delegator = MarketQueryDelegator(reader)
    result = await delegator.get_subscribed_markets()
    assert result == {"TEST"}
    reader.get_subscribed_markets.assert_awaited_once()


@pytest.mark.asyncio
async def test_market_query_delegator_is_market_tracked(reader):
    """Test MarketQueryDelegator.is_market_tracked."""
    delegator = MarketQueryDelegator(reader)
    result = await delegator.is_market_tracked("TEST")
    assert result is True
    reader.is_market_tracked.assert_awaited_once_with("TEST")
