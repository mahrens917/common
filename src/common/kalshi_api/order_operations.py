"""Order operations for Kalshi API."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from common.data_models.trading import OrderRequest, OrderResponse
from common.redis_protocol.error_types import REDIS_ERRORS
from common.trading.order_payloads import build_order_payload

from .client_helpers.errors import KalshiClientError

logger = logging.getLogger(__name__)

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

    async def _execute_order_request(self, method: str, path: str, json_payload: Optional[Any], operation_name: str) -> Any:
        """Execute an order request."""
        method_upper, url, kwargs, op = self._request_builder.build_request_context(
            method=method, path=path, params={}, json_payload=json_payload, operation_name=operation_name
        )
        return await self._request_builder.execute_request(method_upper, url, kwargs, path, op)

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        """Create a new order and return the order response."""
        try:
            payload = build_order_payload(order_request)
        except ValueError as exc:
            raise KalshiClientError(str(exc)) from exc
        logger.debug("Creating order with payload: %s", payload)
        creation_response = await self._execute_order_request("POST", "/trade-api/v2/portfolio/orders", payload, "create_order")
        logger.info("Order creation API response: %s", creation_response)
        order_id = creation_response.get("order_id")
        logger.debug("Extracted order_id: %s (type: %s)", order_id, type(order_id).__name__)
        if not isinstance(order_id, str):
            logger.error(
                "Order creation failed: expected order_id as string, got %s (type: %s). Full response: %s",
                order_id,
                type(order_id).__name__,
                creation_response,
            )
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
        return await self._execute_order_request("DELETE", f"/trade-api/v2/portfolio/orders/{order_id}", None, "cancel_order")

    async def get_order(self, order_id: str, *, trade_rule: Optional[str] = None, trade_reason: Optional[str] = None) -> OrderResponse:
        """Get order details by order ID with optional trade metadata."""
        if not order_id:
            raise KalshiClientError("Order ID must be provided")
        payload = await self._execute_order_request("GET", f"/trade-api/v2/portfolio/orders/{order_id}", None, "get_order")
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
        response_payload = await self._execute_order_request("GET", f"/trade-api/v2/portfolio/orders/{order_id}/fills", None, "get_fills")
        if not isinstance(response_payload, dict):
            raise KalshiClientError("Fills response was not a JSON object")
        fills_raw = response_payload.get("fills")
        if not isinstance(fills_raw, list):
            raise KalshiClientError("Fills response was not a list")
        normalised: List[Dict[str, Any]] = []
        for item in fills_raw:
            if not isinstance(item, dict):
                raise KalshiClientError("Fill entry must be a JSON object")
            normalised.append(self._response_parser.normalise_fill(item))
        return normalised
