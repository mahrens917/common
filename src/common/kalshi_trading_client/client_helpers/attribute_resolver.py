"""Attribute resolver for KalshiTradingClient to keep __getattr__ slim."""

from typing import Any


class ClientAttributeResolver:
    """Resolves attributes for KalshiTradingClient with special handling for state updates."""

    def __init__(self, client):
        self._client = client

    def resolve(self, name: str) -> Any:
        """Resolve attribute by checking API, trade store ops, and private methods."""
        # Public API methods - delegate to _api with special handling for state updates
        if hasattr(self._client._api, name):
            return self._resolve_api_method(name)

        # Trade store operations
        if name in ("_get_trade_store", "_maybe_get_trade_store", "_ensure_trade_store"):
            return self._resolve_trade_store_operation(name)

        # Private methods - delegate to _delegator
        if self._is_delegator_method(name):
            return self._resolve_delegator_method(name)

        raise AttributeError(f"'KalshiTradingClient' has no attribute '{name}'")

    def _resolve_api_method(self, name: str) -> Any:
        """Resolve API method with special wrapper handling for state updates."""
        attr = getattr(self._client._api, name)
        if name == "start_trade_collection":
            return self._wrap_start_trade_collection(attr)
        if name == "stop_trade_collection":
            return self._wrap_stop_trade_collection(attr)
        if name == "require_trade_store":
            return self._wrap_require_trade_store(attr)
        return attr

    def _wrap_start_trade_collection(self, attr):
        """Wrap start_trade_collection to validate trade store and update state."""

        async def _start_wrapper(*args, **kwargs):
            store_getter = getattr(self._client, "_get_trade_store", None)
            if store_getter is None:
                raise ValueError("Trade store required for trade collection")
            try:
                await store_getter()
            except (AttributeError, RuntimeError, ValueError, TypeError) as exc:
                raise ValueError("Trade store required for trade collection") from exc
            self._client.is_running = await attr(*args, **kwargs)

        return _start_wrapper

    def _wrap_stop_trade_collection(self, attr):
        """Wrap stop_trade_collection to update state."""

        async def _stop_wrapper(*args, **kwargs):
            self._client.is_running = await attr(*args, **kwargs)

        return _stop_wrapper

    def _wrap_require_trade_store(self, attr):
        """Wrap require_trade_store to update client's trade_store reference."""

        async def _wrapper(*args, **kwargs):
            store = await attr(*args, **kwargs)
            self._client.trade_store = store
            return store

        return _wrapper

    def _resolve_trade_store_operation(self, name: str):
        """Resolve trade store operations by delegating to TradeStoreOperations."""
        from .trade_store_ops import TradeStoreOperations

        async def _ts_op(*args, **kwargs):
            return await getattr(
                TradeStoreOperations,
                name.replace("_get", "get")
                .replace("_maybe_get", "maybe_get")
                .replace("_ensure", "ensure"),
            )(self._client._trade_store_manager, **kwargs)

        return _ts_op

    def _is_delegator_method(self, name: str) -> bool:
        """Check if name should be resolved via delegator."""
        return (
            name.startswith("_") and hasattr(self._client._delegator, name[1:])
        ) or name == "has_sufficient_balance_for_trade_with_fees"

    def _resolve_delegator_method(self, name: str) -> Any:
        """Resolve method by delegating to _delegator."""
        return getattr(
            self._client._delegator,
            name[1:] if name.startswith("_") else name,
        )
