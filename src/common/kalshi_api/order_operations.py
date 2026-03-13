"""Order operations for Kalshi API."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from common.data_models.trading import (
    _MAX_BATCH_SIZE,
    _MIN_BATCH_SIZE,
    BatchOrderResult,
    OrderAction,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
)
from common.redis_protocol.error_types import REDIS_ERRORS
from common.time_utils import parse_timestamp
from common.trading.order_payloads import build_order_payload

from .client_helpers.errors import KalshiClientError
from .response_field_parser import normalise_fill as normalise_rp_fill
from .response_parser import parse_order_response

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from common.redis_protocol.trade_store import TradeStore

    from .request_builder import RequestBuilder


_DOLLARS_TO_CENTS = 100
_STATUS_NORMALIZE: Dict[str, str] = {"canceled": "cancelled"}


def _parse_creation_response(order_data: Dict[str, Any], order_request: OrderRequest) -> OrderResponse:
    """Build OrderResponse from the POST create order response payload.

    The create endpoint returns fields like fill_count_fp, taker_fees_dollars,
    created_time — different from the GET endpoint's filled_count, fees, timestamp.
    """
    order_id = order_data.get("order_id")
    if not isinstance(order_id, str):
        raise KalshiClientError(f"Creation response missing order_id, got {type(order_id).__name__}")

    try:
        raw_status = str(order_data["status"]).lower()
        status_val = OrderStatus(_STATUS_NORMALIZE.get(raw_status, raw_status))
        side_val = OrderSide(str(order_data["side"]).lower())
        action_val = OrderAction(str(order_data["action"]).lower())
        order_type_val = OrderType(str(order_data["type"]).lower())
        filled_count = int(float(order_data["fill_count_fp"]))
        initial_count = int(float(order_data["initial_count_fp"]))
        taker_fill_cost = float(order_data["taker_fill_cost_dollars"])
        taker_fees = float(order_data["taker_fees_dollars"])
        maker_fees = float(order_data["maker_fees_dollars"])
        timestamp = parse_timestamp(order_data["created_time"])
        client_order_id = str(order_data["client_order_id"])
        ticker = str(order_data["ticker"])
    except (ValueError, KeyError) as exc:
        raise KalshiClientError(f"Invalid field in creation response: {exc}") from exc

    remaining_count = initial_count - filled_count
    avg_fill_price_cents = round(taker_fill_cost * _DOLLARS_TO_CENTS / filled_count) if filled_count else None
    fees_cents = round((taker_fees + maker_fees) * _DOLLARS_TO_CENTS)

    return OrderResponse(
        order_id=order_id,
        client_order_id=client_order_id,
        status=status_val,
        ticker=ticker,
        side=side_val,
        action=action_val,
        order_type=order_type_val,
        filled_count=filled_count,
        remaining_count=remaining_count,
        average_fill_price_cents=avg_fill_price_cents,
        timestamp=timestamp,
        fees_cents=fees_cents,
        fills=[],
        trade_rule=order_request.trade_rule,
        trade_reason=order_request.trade_reason,
    )


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

    def __init__(self, request_builder: RequestBuilder) -> None:
        self._request_builder = request_builder
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
        order_data = creation_response.get("order")
        if not isinstance(order_data, dict):
            raise KalshiClientError(f"Creation response missing order_id, got {type(order_data).__name__}")
        return _parse_creation_response(order_data, order_request)

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
        return parse_order_response(payload, merged_rule, merged_reason)

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
            normalised.append(normalise_rp_fill(item))
        return normalised

    async def batch_create_orders(self, order_requests: List[OrderRequest]) -> List[BatchOrderResult]:
        """Submit a batch of orders in a single API call.

        Uses POST /trade-api/v2/portfolio/orders/batched.
        Maximum 20 orders per batch.
        """
        if len(order_requests) < _MIN_BATCH_SIZE:
            raise KalshiClientError("Batch must contain at least one order")
        if len(order_requests) > _MAX_BATCH_SIZE:
            raise KalshiClientError(f"Batch size {len(order_requests)} exceeds maximum of {_MAX_BATCH_SIZE}")

        payloads = _build_batch_payloads(order_requests)
        batch_payload = {"orders": payloads}
        logger.debug("Submitting batch of %d orders", len(payloads))
        response = await self._execute_order_request(
            "POST",
            "/trade-api/v2/portfolio/orders/batched",
            batch_payload,
            "batch_create_orders",
        )
        return _parse_batch_response(response, order_requests)


def _build_batch_payloads(order_requests: List[OrderRequest]) -> List[Dict[str, Any]]:
    """Build order payloads for a batch request."""
    payloads = []
    for req in order_requests:
        try:
            payloads.append(build_order_payload(req))
        except ValueError as exc:
            raise KalshiClientError(str(exc)) from exc
    return payloads


def _parse_batch_response(
    response: Any,
    order_requests: List[OrderRequest],
) -> List[BatchOrderResult]:
    """Parse the batch order API response into BatchOrderResult list."""
    if not isinstance(response, dict):
        raise KalshiClientError("Batch response was not a JSON object")

    orders_raw = response.get("orders")
    if not isinstance(orders_raw, list):
        raise KalshiClientError("Batch response missing 'orders' list")

    if len(orders_raw) != len(order_requests):
        raise KalshiClientError(f"Batch response count {len(orders_raw)} does not match request count {len(order_requests)}")

    results: List[BatchOrderResult] = []
    for idx, entry in enumerate(orders_raw):
        if not isinstance(entry, dict):
            raise KalshiClientError(f"Batch response entry {idx} is not a JSON object")

        error_code = entry.get("error_code")
        error_message = entry.get("error_message")
        order_response: Optional[OrderResponse] = None

        if error_code is None and "order_id" in entry:
            raw_status = entry.get("status")
            if raw_status is None:
                raise KalshiClientError(f"Batch response entry {idx} missing 'status' field")
            order_response = OrderResponse(
                order_id=entry["order_id"],
                status=_parse_batch_order_status(raw_status),
                ticker=order_requests[idx].ticker,
                side=order_requests[idx].side,
                action=order_requests[idx].action,
                order_type=order_requests[idx].order_type,
                trade_rule=order_requests[idx].trade_rule,
                trade_reason=order_requests[idx].trade_reason,
                client_order_id=order_requests[idx].client_order_id,
            )

        results.append(
            BatchOrderResult(
                order_index=idx,
                order_response=order_response,
                error_code=error_code,
                error_message=error_message,
            )
        )
    return results


def _parse_batch_order_status(raw_status: str) -> OrderStatus:
    """Parse a status string from a batch response entry."""
    try:
        return OrderStatus(raw_status.lower())
    except ValueError as exc:
        raise KalshiClientError(f"Unknown batch order status: {raw_status}") from exc
