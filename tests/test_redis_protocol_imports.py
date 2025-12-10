import importlib

MODULES = [
    "common.redis_protocol.kalshi_store.protocols",
    "common.redis_protocol.kalshi_store.protocols_connections",
    "common.redis_protocol.kalshi_store.protocols_subscriptions",
    "common.redis_protocol.kalshi_store.subscription_factory",
    "common.redis_protocol.parsing.kalshi_helpers",
    "common.redis_protocol.probability_store.keys_helpers",
]


def test_redis_protocol_modules_importable():
    for module_path in MODULES:
        module = importlib.import_module(module_path)
        assert module is not None
