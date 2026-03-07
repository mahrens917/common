"""KalshiStore class setup: properties, static methods, and attribute resolution."""

from __future__ import annotations

from typing import Any

from ..metadata_helpers.timestamp_normalization import normalize_timestamp
from ..utils_coercion import (
    coerce_mapping,
    float_or_default,
    format_probability_value,
    int_or_default,
    normalise_hash,
    string_or_default,
    sync_top_of_book_fields,
)
from ..utils_market import normalise_trade_timestamp

# --- Property management ---


def create_mgr_property(attr: str):
    """Create a managed property that delegates to property manager."""

    def getter(s):
        if hasattr(s, "_property_mgr"):
            return getattr(s._property_mgr, attr)
        return object.__getattribute__(s, f"_{attr}_value") if hasattr(s, f"_{attr}_value") else None

    def setter(s, v):
        if hasattr(s, "_property_mgr"):
            setattr(s._property_mgr, attr, v)
        else:
            object.__setattr__(s, f"_{attr}_value", v)

    return property(getter, setter)


def setup_kalshi_store_properties(store_class) -> None:
    """Set up all properties for KalshiStore class."""
    store_class.redis = create_mgr_property("redis")
    store_class._initialized = create_mgr_property("initialized")
    store_class._pool = create_mgr_property("pool")
    store_class._connection_settings = create_mgr_property("connection_settings")
    store_class._connection_settings_logged = create_mgr_property("connection_settings_logged")
    store_class.SUBSCRIPTIONS_KEY = property(lambda s: s._subscription_delegator.SUBSCRIPTIONS_KEY)
    store_class.SERVICE_STATUS_KEY = property(lambda s: s._subscription_delegator.SERVICE_STATUS_KEY)
    store_class.SUBSCRIBED_MARKETS_KEY = property(lambda s: s._subscription_delegator.SUBSCRIBED_MARKETS_KEY)
    store_class.SUBSCRIPTION_IDS_KEY = property(lambda s: s._subscription_delegator.SUBSCRIPTION_IDS_KEY)


# --- Static method setup ---


def setup_kalshi_store_static_methods(store_class) -> None:
    """Set up all static methods for KalshiStore class."""
    store_class._normalise_hash = staticmethod(normalise_hash)
    store_class._sync_top_of_book_fields = staticmethod(sync_top_of_book_fields)
    store_class._format_probability_value = staticmethod(format_probability_value)
    store_class._normalize_timestamp = staticmethod(normalize_timestamp)
    store_class._normalise_trade_timestamp = staticmethod(normalise_trade_timestamp)
    store_class._coerce_mapping = staticmethod(coerce_mapping)
    store_class._string_or_default = staticmethod(string_or_default)
    store_class._int_or_default = staticmethod(int_or_default)
    store_class._float_or_default = staticmethod(float_or_default)


# --- Attribute resolution ---


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
    ):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    attr_resolver = object.__getattribute__(self, "_attr_resolver")
    return attr_resolver.resolve(name)
