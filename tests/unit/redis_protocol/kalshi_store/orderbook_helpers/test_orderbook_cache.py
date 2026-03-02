"""Tests for OrderbookCache and MarketUpdate."""

from common.redis_protocol.kalshi_store.orderbook_helpers.orderbook_cache import (
    MarketUpdate,
    OrderbookCache,
)


class TestOrderbookCache:
    def test_get_field_empty(self) -> None:
        cache = OrderbookCache()
        assert cache.get_field("key1", "field1") is None

    def test_store_snapshot_and_get_field(self) -> None:
        cache = OrderbookCache()
        cache.store_snapshot("key1", {"yes_bid": "50", "yes_ask": "60"})
        assert cache.get_field("key1", "yes_bid") == "50"
        assert cache.get_field("key1", "yes_ask") == "60"
        assert cache.get_field("key1", "nonexistent") is None

    def test_store_snapshot_replaces_all(self) -> None:
        cache = OrderbookCache()
        cache.store_snapshot("key1", {"a": "1", "b": "2"})
        cache.store_snapshot("key1", {"c": "3"})
        assert cache.get_field("key1", "a") is None
        assert cache.get_field("key1", "c") == "3"

    def test_update_fields_returns_full_state(self) -> None:
        cache = OrderbookCache()
        cache.store_snapshot("key1", {"a": "1", "b": "2"})
        result = cache.update_fields("key1", {"b": "99", "c": "3"})
        assert result == {"a": "1", "b": "99", "c": "3"}

    def test_update_fields_creates_entry_if_absent(self) -> None:
        cache = OrderbookCache()
        result = cache.update_fields("key1", {"x": "10"})
        assert result == {"x": "10"}

    def test_update_fields_returns_reference(self) -> None:
        cache = OrderbookCache()
        cache.store_snapshot("key1", {"a": "1"})
        result = cache.update_fields("key1", {"b": "2"})
        # Returns the internal dict by reference for read-only callers
        assert result is cache.update_fields("key1", {})

    def test_get_snapshot_returns_reference(self) -> None:
        cache = OrderbookCache()
        cache.store_snapshot("key1", {"a": "1"})
        cache.update_fields("key1", {"b": "2"})
        snapshot = cache.get_snapshot("key1")
        assert snapshot == {"a": "1", "b": "2"}
        assert snapshot is cache.get_snapshot("key1")

    def test_get_snapshot_missing_key(self) -> None:
        cache = OrderbookCache()
        assert cache.get_snapshot("nonexistent") is None

    def test_store_snapshot_is_isolated_copy(self) -> None:
        cache = OrderbookCache()
        original = {"a": "1"}
        cache.store_snapshot("key1", original)
        original["b"] = "2"
        assert cache.get_field("key1", "b") is None


class TestMarketUpdate:
    def test_fields(self) -> None:
        update = MarketUpdate(
            market_key="key1",
            market_ticker="TICKER-A",
            fields={"yes_bid": "50"},
            timestamp="12345",
        )
        assert update.market_key == "key1"
        assert update.market_ticker == "TICKER-A"
        assert update.fields == {"yes_bid": "50"}
        assert update.timestamp == "12345"

    def test_frozen(self) -> None:
        update = MarketUpdate(market_key="k", market_ticker="t", fields={}, timestamp="0")
        try:
            update.market_key = "other"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised
