"""Property management for KalshiStore."""


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
