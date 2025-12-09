from src.common.redis_protocol.kalshi_store.subscription_helpers.key_provider import KeyProvider


def test_key_provider_properties():
    provider = KeyProvider("rest")
    assert provider.subscriptions_key == "kalshi:subscriptions"
    assert provider.service_status_key == "status"
    assert provider.subscribed_markets_key == "kalshi:subscribed_markets"
    assert provider.subscription_ids_key.endswith(":rest")
