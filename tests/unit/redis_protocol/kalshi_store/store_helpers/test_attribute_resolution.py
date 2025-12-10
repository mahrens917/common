"""Tests for Kalshi store attribute resolution helper."""

import pytest

from common.redis_protocol.kalshi_store.store_helpers import attribute_resolution


class DummyResolver:
    def __init__(self):
        self.resolved = {}

    def resolve(self, name: str):
        self.resolved[name] = self.resolved.get(name, 0) + 1
        return f"resolved:{name}"


class DummyStore:
    def __init__(self):
        self._attr_resolver = DummyResolver()
        self._reader = "reader-obj"
        self.existing = "value"

    __getattr__ = attribute_resolution.kalshi_store_getattr


def test_kalshi_store_getattr_delegates_to_resolver():
    store = DummyStore()
    assert store.some_field == "resolved:some_field"
    assert store._attr_resolver.resolved["some_field"] == 1


def test_kalshi_store_getattr_returns_private_field():
    store = DummyStore()
    assert store._reader == "reader-obj"


def test_kalshi_store_getattr_missing_private_field():
    store = DummyStore()
    del store._reader

    with pytest.raises(AttributeError):
        _ = store._reader
