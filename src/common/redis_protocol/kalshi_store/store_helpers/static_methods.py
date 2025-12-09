"""Static method setup for KalshiStore."""

from ..facade_helpers import StaticUtilities


def setup_kalshi_store_static_methods(store_class) -> None:
    """Set up all static methods for KalshiStore class."""
    store_class._normalise_hash = staticmethod(StaticUtilities.normalise_hash)
    store_class._sync_top_of_book_fields = staticmethod(StaticUtilities.sync_top_of_book_fields)
    store_class._format_probability_value = staticmethod(StaticUtilities.format_probability_value)
    store_class._normalize_timestamp = staticmethod(StaticUtilities.normalize_timestamp)
    store_class._normalise_trade_timestamp = staticmethod(StaticUtilities.normalise_trade_timestamp)
    store_class._coerce_mapping = staticmethod(StaticUtilities.coerce_mapping)
    store_class._string_or_default = staticmethod(StaticUtilities.string_or_default)
    store_class._int_or_default = staticmethod(StaticUtilities.int_or_default)
    store_class._float_or_default = staticmethod(StaticUtilities.float_or_default)
