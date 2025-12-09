from __future__ import annotations

import pytest

from src.common.redis_schema.operations import (
    MetricStreamKey,
    ServiceStatusKey,
    SubscriptionKey,
    SubscriptionType,
)
from src.common.redis_schema.validators import register_namespace, validate_registered_key


def test_register_namespace_detects_conflicts(monkeypatch):
    monkeypatch.setattr(
        "src.common.redis_schema.validators._registered_prefixes", {}, raising=False
    )

    register_namespace("ops:test:", "Test namespace")
    register_namespace("ops:test:", "Test namespace")  # idempotent

    with pytest.raises(ValueError):
        register_namespace("ops:test:", "Different description")


def test_validate_registered_key(monkeypatch):
    monkeypatch.setattr(
        "src.common.redis_schema.validators._registered_prefixes", {}, raising=False
    )
    register_namespace("ops:status:", "Status keys")

    validate_registered_key("ops:status:tracker")  # should not raise

    with pytest.raises(ValueError):
        validate_registered_key("unknown:status")


def test_operations_key_builders():
    subscription = SubscriptionKey("Deribit")
    assert subscription.key() == "ops:subscriptions:deribit"
    assert subscription.field(SubscriptionType.PRICE_INDEX, "BTC_USD") == "price_index:btc_usd"

    status = ServiceStatusKey("Tracker")
    assert status.key() == "ops:status:tracker"

    metric = MetricStreamKey("Weather", "latency", "5m")
    assert metric.key() == "ops:metrics:weather:latency:5m"
