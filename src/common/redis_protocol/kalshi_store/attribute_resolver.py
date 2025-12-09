"""Centralized attribute resolution for KalshiStore to keep __getattr__ slim."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AttributeResolverDelegators:
    """Configuration for AttributeResolver delegator components."""

    storage_delegator: Any
    write_delegator: Any
    utility_delegator: Any
    conn_delegator: Any
    metadata_delegator: Any
    subscription_delegator: Any
    query_delegator: Any
    orderbook_delegator: Any
    cleanup_delegator: Any


class AttributeResolver:
    """Resolves attributes dynamically for KalshiStore facade."""

    _NOT_FOUND = object()

    # Method name mappings for utility methods
    UTILITY_METHOD_MAP = {
        "_store_optional_field": "store_optional_field",
        "_update_trade_prices_for_market": "update_trade_prices_for_market",
        "_market_descriptor": "market_descriptor",
        "_derive_expiry_iso": "derive_expiry_iso",
        "_extract_weather_station_from_ticker": "extract_weather_station_from_ticker",
        "_ensure_market_metadata_fields": "ensure_market_metadata_fields",
        "_aggregate_markets_by_point": "aggregate_markets_by_point",
        "_build_strike_summary": "build_strike_summary",
    }

    def __init__(self, delegators: AttributeResolverDelegators):
        self._storage = delegators.storage_delegator
        self._write = delegators.write_delegator
        self._utility = delegators.utility_delegator
        self._connection = delegators.conn_delegator
        self._metadata = delegators.metadata_delegator
        self._query = delegators.query_delegator
        self._delegators = [
            delegators.conn_delegator,
            delegators.metadata_delegator,
            delegators.subscription_delegator,
            delegators.query_delegator,
            delegators.write_delegator,
            delegators.orderbook_delegator,
            delegators.cleanup_delegator,
            delegators.utility_delegator,
            delegators.storage_delegator,
        ]

    def resolve(self, name: str) -> Any:
        """Resolve attribute by checking utility methods then delegators."""
        special = self._resolve_special(name)
        if special is not self._NOT_FOUND:
            return special

        utility = self._resolve_utility(name)
        if utility is not self._NOT_FOUND:
            return utility

        delegator_attr = self._resolve_delegator_attr(name)
        if delegator_attr is not self._NOT_FOUND:
            return delegator_attr

        # Not found
        raise AttributeError(f"'KalshiStore' has no attribute '{name}'")

    def _resolve_special(self, name: str) -> Any:
        """Handle hard-coded attribute translations."""
        mapping = {
            "_resolve_connection_settings": (self._connection, "resolve_connection_settings"),
            "_acquire_pool": (self._connection, "acquire_pool"),
            "_build_kalshi_metadata": (self._metadata, "build_kalshi_metadata"),
            "_get_market_field": (self._query, "get_market_field"),
            "_connect_with_retry": (self._connection, "connect_with_retry"),
        }
        target = mapping.get(name)
        if not target:
            return self._NOT_FOUND
        delegator, attribute = target
        return getattr(delegator, attribute)

    def _resolve_utility(self, name: str) -> Any:
        """Resolve utility-based attribute names."""
        if name not in self.UTILITY_METHOD_MAP:
            return self._NOT_FOUND

        target_method = self.UTILITY_METHOD_MAP[name]
        if name == "_store_optional_field":
            return getattr(self._storage, target_method)
        if name == "_update_trade_prices_for_market":
            return getattr(self._write, target_method)
        return getattr(self._utility, target_method)

    def _resolve_delegator_attr(self, name: str) -> Any:
        """Search delegators for matching attribute."""
        for delegator in self._delegators:
            if hasattr(delegator, name):
                return getattr(delegator, name)
        return self._NOT_FOUND
