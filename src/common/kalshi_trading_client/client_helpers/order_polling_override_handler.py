"""Handles create_order_with_polling method override logic."""

from typing import Any, Callable, Optional

from ...data_models.trading import OrderRequest, OrderResponse


class OrderPollingOverrideHandler:
    """Manages override behavior for create_order_with_polling."""

    def __init__(self, orders_service: Any, api_delegator: Any):
        self._orders = orders_service
        self._api = api_delegator

    def _save_original_state(self) -> dict[str, Any]:
        """Save original service state before applying overrides."""
        return {
            "create": self._orders.create_order,
            "poller_factory": getattr(self._orders._poller, "_poller_factory", None),
            "finalizer_factory": getattr(self._orders._poller, "_finalizer_factory", None),
            "cancel": getattr(self._api, "_cancel_order_fn", None),
        }

    def _apply_overrides(
        self,
        proxy: Callable,
        override_cancel: Optional[Callable],
        poller_builder: Optional[Callable],
        finalizer_builder: Optional[Callable],
        original_state: dict[str, Any],
    ) -> None:
        """Apply all overrides to service."""
        self._orders.create_order = proxy

        if override_cancel is not None:
            self._api._cancel_order_fn = override_cancel

        if original_state["poller_factory"] is not None and poller_builder is not None:
            self._orders._poller._poller_factory = poller_builder

        if original_state["finalizer_factory"] is not None and finalizer_builder is not None:
            self._orders._poller._finalizer_factory = finalizer_builder

    def _restore_original_state(self, original_state: dict[str, Any], override_cancel: Optional[Callable]) -> None:
        """Restore original service state after execution."""
        self._orders.create_order = original_state["create"]

        if original_state["poller_factory"] is not None:
            self._orders._poller._poller_factory = original_state["poller_factory"]

        if original_state["finalizer_factory"] is not None:
            self._orders._poller._finalizer_factory = original_state["finalizer_factory"]

        if override_cancel is not None and original_state["cancel"] is not None:
            self._api._cancel_order_fn = original_state["cancel"]

    async def create_order_with_polling(
        self,
        order_request: OrderRequest,
        timeout_seconds: int,
        override_create: Optional[Callable],
        override_cancel: Optional[Callable],
        poller_builder: Optional[Callable],
        finalizer_builder: Optional[Callable],
    ) -> OrderResponse:
        """Execute create_order_with_polling with optional overrides."""
        if override_create is None:
            return await self._api.create_order_with_polling(order_request, timeout_seconds)

        async def proxy(request: OrderRequest) -> OrderResponse:
            return await override_create(request)

        original_state = self._save_original_state()

        try:
            self._apply_overrides(proxy, override_cancel, poller_builder, finalizer_builder, original_state)
            return await self._api.create_order_with_polling(order_request, timeout_seconds)
        finally:
            self._restore_original_state(original_state, override_cancel)
