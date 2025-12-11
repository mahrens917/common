"""Tests for Kalshi store subscription writer helpers."""

from typing import Any, Dict

import pytest

from common.redis_protocol.kalshi_store.writer_helpers import subscription_writer


class DummyMetadataAdapter:
    def __init__(self):
        self.calls = []

    def extract_weather_station_from_ticker(self, ticker: str) -> str:
        self.calls.append(("station", ticker))
        return "KJFK"

    def derive_expiry_iso(self, market_ticker: str, metadata: Dict[str, Any], expiry_token: str) -> str:
        self.calls.append(("expiry", market_ticker, expiry_token))
        return "2025-01-01T00:00:00Z"

    def ensure_market_metadata_fields(self, market_ticker: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append(("ensure", market_ticker))
        return metadata


def test_subscription_writer_delegates_to_metadata_adapter():
    adapter = DummyMetadataAdapter()
    writer = subscription_writer.SubscriptionWriter(redis_connection=None, logger_instance=None, metadata_adapter=adapter)

    assert writer.extract_weather_station_from_ticker("KXHIGHTEST") == "KJFK"
    assert writer.derive_expiry_iso("KXHIGHTEST", {"foo": "bar"}, type("Desc", (), {"expiry_token": "token"})) == "2025-01-01T00:00:00Z"
    assert writer.ensure_market_metadata_fields("KXHIGHTEST", {"foo": "bar"}) == {"foo": "bar"}
    assert adapter.calls[0][0] == "station"
    assert adapter.calls[1][0] == "expiry"
    assert adapter.calls[2][0] == "ensure"


def test_select_timestamp_value_calls_helper(monkeypatch):
    import common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization as tn

    called = {}

    def fake_select(data: Dict, fields):
        called["args"] = (data, tuple(fields))
        return "selected"

    monkeypatch.setattr(tn, "select_timestamp_value", fake_select)

    result = subscription_writer.SubscriptionWriter.select_timestamp_value({"foo": "bar"}, ["close_time"])
    assert result == "selected"
    assert called["args"][0] == {"foo": "bar"}


def test_normalize_timestamp_calls_helper(monkeypatch):
    import common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization as tn

    called = {}

    def fake_normalize(value: Any):
        called["value"] = value
        return "2025-01-01T00:00:00Z"

    monkeypatch.setattr(tn, "normalize_timestamp", fake_normalize)

    assert subscription_writer.SubscriptionWriter.normalize_timestamp("value") == "2025-01-01T00:00:00Z"
    assert called["value"] == "value"
