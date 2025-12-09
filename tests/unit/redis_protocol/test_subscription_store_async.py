from __future__ import annotations

import pytest

from src.common.redis_protocol import config as redis_config
from src.common.redis_protocol.messages import InstrumentMetadata, SubscriptionUpdate
from src.common.redis_protocol.subscription_store import SubscriptionStore


def _make_store(fake) -> SubscriptionStore:
    store = SubscriptionStore(service_type="kalshi")
    store.redis = fake
    store._initialized = True
    return store


def _sample_update(channel: str = "kalshi.channel.test") -> SubscriptionUpdate:
    metadata = InstrumentMetadata(
        type="option",
        channel=channel,
        currency="BTC",
        expiry="31JAN25",
        strike=50000,
        option_type="call",
    )
    return SubscriptionUpdate(
        name="BTC-31JAN25-50000-C",
        subscription_type="instrument",
        action="subscribe",
        metadata=metadata,
    )


@pytest.mark.asyncio
async def test_add_and_remove_subscription(fake_redis_client_factory):
    fake = fake_redis_client_factory()
    store = _make_store(fake)

    update = _sample_update()

    added = await store.add_subscription(update)
    assert added is True

    subscription_hash = redis_config.KALSHI_SUBSCRIPTION_KEY
    assert fake.dump_hash(subscription_hash) == {
        "instrument:BTC-31JAN25-50000-C": update.metadata.channel
    }
    assert fake.published[-1][0] == redis_config.KALSHI_SUBSCRIPTION_CHANNEL

    active = await store.get_active_subscriptions()
    assert active["instruments"]["BTC-31JAN25-50000-C"] == update.metadata.channel
    counts = await store.verify_subscriptions()
    assert counts == {"instruments": 1, "price_indices": 0, "volatility_indices": 0}

    removed = await store.remove_subscription(update)
    assert removed is True
    assert fake.dump_hash(subscription_hash) == {}
    assert fake.published[-1][0] == redis_config.KALSHI_SUBSCRIPTION_CHANNEL


@pytest.mark.asyncio
async def test_add_subscription_rejects_invalid_channel(fake_redis_client_factory):
    fake = fake_redis_client_factory()
    store = _make_store(fake)

    update = _sample_update(channel="1234")

    result = await store.add_subscription(update)
    assert result is False
    assert fake.dump_hash(redis_config.KALSHI_SUBSCRIPTION_KEY) == {}


@pytest.mark.asyncio
async def test_remove_subscription_handles_pipeline_errors(fake_redis_client_factory):
    fake = fake_redis_client_factory()
    store = _make_store(fake)
    update = _sample_update()

    class FailingPipeline:
        def hdel(self, *args, **kwargs):
            return self

        def publish(self, *args, **kwargs):
            return self

        async def execute(self):
            raise RuntimeError("fail")

    fake.pipeline = lambda **kwargs: FailingPipeline()

    assert await store.remove_subscription(update) is False


@pytest.mark.asyncio
async def test_get_active_subscriptions_handles_error(fake_redis_client_factory, monkeypatch):
    fake = fake_redis_client_factory()
    store = _make_store(fake)

    async def fail():
        raise RuntimeError("boom")

    monkeypatch.setattr(store, "_get_redis", fail)
    result = await store.get_active_subscriptions()
    assert result == {}


@pytest.mark.asyncio
async def test_verify_subscriptions_handles_error(fake_redis_client_factory, monkeypatch):
    fake = fake_redis_client_factory()
    store = _make_store(fake)

    async def fail():
        raise RuntimeError("boom")

    monkeypatch.setattr(store, "_get_redis", fail)
    counts = await store.verify_subscriptions()
    assert counts == {"instruments": 0, "price_indices": 0, "volatility_indices": 0}
