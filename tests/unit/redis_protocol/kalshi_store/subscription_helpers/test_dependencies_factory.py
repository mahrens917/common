import logging

from common.redis_protocol.kalshi_store.subscription_helpers import dependencies_factory


def test_create_dependencies_returns_container(monkeypatch):
    class DummyConnection:
        pass

    class DummyLogger:
        pass

    class DummyRedisConnectionManager:
        pass

    deps = dependencies_factory.KalshiSubscriptionTrackerDependenciesFactory.create(
        redis_connection=DummyRedisConnectionManager(),
        logger_instance=logging.getLogger("tests"),
        service_prefix="ws",
    )
    assert deps.connection_manager is not None
    assert deps.key_provider.subscriptions_key == "kalshi:subscriptions"
    assert deps.market_subscription_manager is not None
