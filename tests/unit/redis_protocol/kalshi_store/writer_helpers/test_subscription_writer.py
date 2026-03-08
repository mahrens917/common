"""Tests for Kalshi store subscription writer helpers."""

from typing import Any, Dict

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


def test_derive_expiry_iso_empty_token_calls_with_none():
    """When expiry_token is empty, derive_expiry_iso passes None to the adapter."""
    adapter = DummyMetadataAdapter()
    writer = subscription_writer.SubscriptionWriter(redis_connection=None, logger_instance=None, metadata_adapter=adapter)

    writer.derive_expiry_iso("TICKER", {}, type("Desc", (), {"expiry_token": ""})())
    assert adapter.calls[0] == ("expiry", "TICKER", None)
