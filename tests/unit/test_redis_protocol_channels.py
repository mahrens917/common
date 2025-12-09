from src.common.redis_protocol.channels import (
    OptimizedMarketStore,
    SubscriptionStore,
)
from src.common.redis_protocol.channels import __all__ as exported


def test_channel_reexports():
    assert {"OptimizedMarketStore", "SubscriptionStore"} <= set(exported)
    assert SubscriptionStore is not None
    assert OptimizedMarketStore is not None
