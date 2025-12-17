"""Order operations for Kalshi API."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from common.data_models.trading import OrderRequest, OrderResponse
from common.redis_protocol.error_types import REDIS_ERRORS
from common.trading.order_payloads import build_order_payload

from .client_helpers.errors import KalshiClientError

if TYPE_CHECKING:
    from common.redis_protocol.trade_store import TradeStore

    from .request_builder import RequestBuilder
    from .response_parser import ResponseParser


class OrderMetadataManager:
    """Manages order metadata retrieval from trade store."""

    def __init__(self, trade_store_errors):
        self._trade_store: Optional[TradeStore] = None
        self._trade_store_errors = trade_store_errors

    def attach_trade_store(self, trade_store: TradeStore | None) -> None:
        """Attach a trade store for order metadata retrieval."""
        if trade_store is None:
            raise KalshiClientError("Trade store must not be None")
        self._trade_store = trade_store

    async def fetch_metadata(self, order_id: str) -> Dict[str, str]:
        """Fetch order metadata from trade store."""
        store = await self._require_trade_store()
        try:
            metadata = await store.get_order_metadata(order_id)
        except self._trade_store_errors as exc:
            raise KalshiClientError(f"Failed to fetch trade metadata for order {order_id}") from exc
        if not metadata:
            raise KalshiClientError(f"Trade metadata missing for order {order_id}")
        return metadata

    async def _require_trade_store(self) -> TradeStore:
        if self._trade_store is None:
            raise KalshiClientError("Kalshi trade store is not configured")
        if hasattr(self._trade_store, "initialize"):
            try:
                result = self._trade_store.initialize()
                if inspect.isawaitable(result):
                    await result
            except self._trade_store_errors as exc:
                raise KalshiClientError("Failed to initialize trade store") from exc
        return self._trade_store


class OrderOperations:
    """Handles order-related API operations."""

    def __init__(self, request_builder: RequestBuilder, response_parser: ResponseParser) -> None:
        self._request_builder = request_builder
        self._response_parser = response_parser
        self._trade_store_errors = REDIS_ERRORS + (
            KalshiClientError,
            ConnectionError,
            RuntimeError,
            ValueError,
            TypeError,
        )
        self._metadata_manager = OrderMetadataManager(self._trade_store_errors)

    def attach_trade_store(self, trade_store: TradeStore) -> None:
        """Attach a trade store for order metadata operations."""
        self._metadata_manager.attach_trade_store(trade_store)

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Create a new order and return the order response."""
        try:
            payload = build_order_payload(order_request)
        except ValueError as exc:
            raise KalshiClientError(str(exc)) from exc
        method_upper, url, kwargs, op = self._request_builder.build_request_context(
            method="POST",
            path="/trade-api/v2/portfolio/orders",
            params=None,
            json_payload=payload,
            operation_name="create_order",
        )
        creation_response = await self._request_builder.execute_request(method_upper, url, kwargs, "/trade-api/v2/portfolio/orders", op)
        order_id = creation_response.get("order_id")
        if not isinstance(order_id, str):
            raise KalshiClientError("Order creation response missing 'order_id'")
        return await self.get_order(
            order_id,
            trade_rule=order_request.trade_rule,
            trade_reason=order_request.trade_reason,
        )

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order by order ID."""
        if not order_id:
            raise KalshiClientError("Order ID must be provided for cancellation")
        method_upper, url, kwargs, op = self._request_builder.build_request_context(
            method="DELETE",
            path=f"/trade-api/v2/portfolio/orders/{order_id}",
            params={},
            json_payload=None,
            operation_name="cancel_order",
        )
        return await self._request_builder.execute_request(method_upper, url, kwargs, f"/trade-api/v2/portfolio/orders/{order_id}", op)

    async def get_order(
        self,
        order_id: str,
        *,
        trade_rule: Optional[str] = None,
        trade_reason: Optional[str] = None,
    ) -> OrderResponse:
        """Get order details by order ID with optional trade metadata."""
        if not order_id:
            raise KalshiClientError("Order ID must be provided")
        method_upper, url, kwargs, op = self._request_builder.build_request_context(
            method="GET",
            path=f"/trade-api/v2/portfolio/orders/{order_id}",
            params={},
            json_payload=None,
            operation_name="get_order",
        )
        payload = await self._request_builder.execute_request(method_upper, url, kwargs, f"/trade-api/v2/portfolio/orders/{order_id}", op)
        metadata: Dict[str, str] = {}
        if trade_rule is None or trade_reason is None:
            metadata = await self._metadata_manager.fetch_metadata(order_id)
        merged_rule = trade_rule if trade_rule else metadata.get("trade_rule")
        merged_reason = trade_reason if trade_reason else metadata.get("trade_reason")
        return self._response_parser.parse_order_response(payload, merged_rule, merged_reason)

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        """Get fills for an order by order ID."""
        if not order_id:
            raise KalshiClientError("Order ID must be provided")
        method_upper, url, kwargs, op = self._request_builder.build_request_context(
            method="GET",
            path=f"/trade-api/v2/portfolio/orders/{order_id}/fills",
            params={},
            json_payload=None,
            operation_name="get_fills",
        )
        response_payload: Any = await self._request_builder.execute_request(
            method_upper, url, kwargs, f"/trade-api/v2/portfolio/orders/{order_id}/fills", op
        )
        if not isinstance(response_payload, dict):
            raise KalshiClientError("Fills response was not a JSON object")
        payload = response_payload
        fills_raw = payload.get("fills")
        if not isinstance(fills_raw, list):
            raise KalshiClientError("Fills response was not a list")
        normalised: List[Dict[str, Any]] = []
        for item in fills_raw:
            if not isinstance(item, dict):
                raise KalshiClientError("Fill entry must be a JSON object")
            normalised.append(self._response_parser.normalise_fill(item))
        return normalised
