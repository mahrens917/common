"""Attribute resolution for KalshiStore."""

from typing import Any


def kalshi_store_getattr(self, name: str) -> Any:
    """Custom __getattr__ for KalshiStore with delegation support."""
    if name.startswith("_") and name in (
        "_attr_resolver",
        "_connection",
        "_metadata",
        "_subscription",
        "_reader",
        "_writer",
        "_cleaner",
        "_orderbook",
        "_conn_delegator",
        "_metadata_delegator",
        "_subscription_delegator",
        "_query_delegator",
        "_write_delegator",
        "_orderbook_delegator",
        "_cleanup_delegator",
        "_utility_delegator",
        "_storage_delegator",
    ):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    attr_resolver = object.__getattribute__(self, "_attr_resolver")
    return attr_resolver.resolve(name)
