import importlib

MODULES = [
    "src.common.redis_protocol.kalshi_store.protocols",
    "src.common.redis_protocol.kalshi_store.protocols_connections",
    "src.common.redis_protocol.kalshi_store.protocols_subscriptions",
    "src.common.redis_protocol.kalshi_store.subscription_factory",
    "src.common.redis_protocol.parsing.kalshi_helpers",
    "src.common.redis_protocol.probability_store.keys_helpers",
]


def test_redis_protocol_modules_importable():
    for module_path in MODULES:
        module = importlib.import_module(module_path)
        assert module is not None
