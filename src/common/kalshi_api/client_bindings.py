"""Kalshi API client bindings for trading operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiohttp

from common.data_models.trading import (
    BatchOrderResult,
    OrderRequest,
    OrderResponse,
    PortfolioBalance,
    PortfolioPosition,
)
from common.trading.order_payloads import build_order_payload

from .client_helpers import KalshiClientError
from .client_helpers.property_accessors import get_initialized as _get_initialized
from .client_helpers.property_accessors import get_session_lock as _get_session_lock
from .client_helpers.property_accessors import get_trade_store as _get_trade_store
from .client_helpers.property_accessors import set_initialized as _set_initialized
from .client_helpers.property_accessors import set_session_lock as _set_session_lock
from .client_helpers.property_accessors import set_trade_store as _set_trade_store

HTTP_ERROR_STATUS_THRESHOLD = 400


async def _initialize(client) -> None:
    session = client.__dict__.get("_cached_session", None)
    closed_attr = getattr(session, "closed", None)
    if closed_attr is None:
        session_closed = False
    else:
        session_closed = bool(closed_attr)
    if session is not None and not session_closed:
        client.initialized = True
        return
    session_manager = getattr(client, "_session_manager", None)
    if session_manager is None:
        raise KalshiClientError("KalshiClient session manager is not initialized")
    await session_manager.initialize()
    client.initialized = True
    client.session = session_manager.get_session()


async def _close(client) -> None:
    session_manager = getattr(client, "_session_manager", None)
    if session_manager is not None:
        await session_manager.close()
    client.initialized = False
    client.session = None


def _attach_trade_store(client, trade_store: Optional[Any]) -> None:
    if trade_store is None:
        raise KalshiClientError("Trade store must not be None")
    order_ops = getattr(client, "_order_ops", None)
    attach = getattr(order_ops, "attach_trade_store", None)
    if callable(attach):
        attach(trade_store)
    client.trade_store = trade_store


def _build_request_kwargs(
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]],
    json: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build request kwargs from components."""
    request_kwargs: Dict[str, Any] = {"headers": headers}
    if params is not None:
        request_kwargs["params"] = params
    if json is not None:
        request_kwargs["json"] = json
    return request_kwargs


def _build_url(base_url: str, path: str) -> str:
    """Build full URL from base and path."""
    base_url_clean = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base_url_clean}{normalized_path}"


async def _execute_request(session, method_upper: str, url: str, request_kwargs: Dict[str, Any]):
    """Execute HTTP request and validate response."""
    request_context = session.request(method_upper, url, **request_kwargs)
    if hasattr(request_context, "__aenter__"):
        async with request_context as response:
            actual_response = _unwrap_response(response)
            if actual_response.status >= HTTP_ERROR_STATUS_THRESHOLD:
                raise KalshiClientError(f"KalshiClient API request failed (status: {actual_response.status})")
            return await actual_response.json()

    response = await request_context
    actual_response = _unwrap_response(response)
    if actual_response.status >= HTTP_ERROR_STATUS_THRESHOLD:
        raise KalshiClientError(f"KalshiClient API request failed (status: {actual_response.status})")
    return await actual_response.json()


async def _api_request_impl(
    client,
    *,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    operation_name: Optional[str] = None,
) -> Dict[str, Any]:
    builder = getattr(client, "_request_builder", None)
    method_upper = method.upper()
    if builder is not None:
        method_upper, url, request_kwargs, op = builder.build_request_context(
            method=method,
            path=path,
            params=params,
            json_payload=json,
            operation_name=operation_name,
        )
        await client.initialize()
        request_kwargs["headers"] = client.auth_headers(method_upper, path)
        return await builder.execute_request(method_upper, url, request_kwargs, path, op)

    await client.initialize()
    session = client.__dict__.get("_cached_session", None)
    if session is None:
        raise KalshiClientError("KalshiClient session is not initialized")

    headers = client.auth_headers(method_upper, path)
    request_kwargs = _build_request_kwargs(headers, params, json)
    url = _build_url(getattr(client, "_config").base_url, path)

    return await _execute_request(session, method_upper, url, request_kwargs)


async def _direct_api_request_impl(
    client,
    *,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    operation_name: Optional[str] = None,
) -> Dict[str, Any]:
    if not path.startswith("/"):
        raise KalshiClientError("Path must begin with '/' for direct requests")

    session = client.__dict__.get("_cached_session", None)
    if session is None:
        raise KalshiClientError("HTTP session is not initialized")

    method_upper = method.upper()
    headers = getattr(client, "_auth_headers")(method_upper, path)
    request_kwargs = _build_request_kwargs(headers, params, json)
    url = _build_url(getattr(client, "_config").base_url, path)

    try:
        response = await session.request(method_upper, url, **request_kwargs)
    except aiohttp.ClientError as exc:
        raise KalshiClientError("Kalshi request failed") from exc

    if response.status >= HTTP_ERROR_STATUS_THRESHOLD:
        raise KalshiClientError(f"Direct request {path} returned {response.status}")

    try:
        payload = await response.json()
    except aiohttp.ContentTypeError as exc:
        target = operation_name if operation_name is not None else path
        raise KalshiClientError(f"Direct request {target} was not JSON") from exc

    if not isinstance(payload, dict):
        raise KalshiClientError("Direct request response was not a JSON object")

    return payload


async def _get_portfolio_balance_impl(client) -> PortfolioBalance:
    portfolio_ops = getattr(client, "_portfolio_ops", None)
    if portfolio_ops is None:
        raise KalshiClientError("Portfolio operations not initialized")
    return await portfolio_ops.get_balance()


async def _get_portfolio_positions_impl(client) -> List[PortfolioPosition]:
    portfolio_ops = getattr(client, "_portfolio_ops", None)
    if portfolio_ops is None:
        raise KalshiClientError("Portfolio operations not initialized")
    return await portfolio_ops.get_positions()


async def _create_order_impl(client, order_request: OrderRequest) -> OrderResponse:
    order_ops = getattr(client, "_order_ops", None)
    if order_ops is None:
        raise KalshiClientError("Order operations not initialized")
    return await order_ops.create_order(order_request)


async def _cancel_order_impl(client, order_id: str) -> Dict[str, Any]:
    order_ops = getattr(client, "_order_ops", None)
    if order_ops is None:
        raise KalshiClientError("Order operations not initialized")
    return await order_ops.cancel_order(order_id)


async def _get_order_impl(
    client,
    order_id: str,
    *,
    trade_rule: Optional[str] = None,
    trade_reason: Optional[str] = None,
) -> OrderResponse:
    order_ops = getattr(client, "_order_ops", None)
    if order_ops is None:
        raise KalshiClientError("Order operations not initialized")
    return await order_ops.get_order(
        order_id,
        trade_rule=trade_rule,
        trade_reason=trade_reason,
    )


async def _get_fills_impl(client, order_id: str) -> List[Dict[str, Any]]:
    order_ops = getattr(client, "_order_ops", None)
    if order_ops is None:
        raise KalshiClientError("Order operations not initialized")
    return await order_ops.get_fills(order_id)


async def _get_series_impl(client, *, category: Optional[str] = None) -> List[Dict[str, Any]]:
    series_ops = getattr(client, "_series_ops", None)
    if series_ops is None:
        raise KalshiClientError("Series operations not initialized")
    return await series_ops.get_series(category=category)


async def _get_all_fills_impl(
    client,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
    ticker: Optional[str] = None,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    fills_ops = getattr(client, "_fills_ops", None)
    if fills_ops is None:
        raise KalshiClientError("Fills operations not initialized")
    return await fills_ops.get_all_fills(min_ts, max_ts, ticker, cursor)


async def _get_exchange_status_impl(client) -> Dict[str, bool]:
    market_status_ops = getattr(client, "_market_status_ops", None)
    if market_status_ops is None:
        raise KalshiClientError("Market status operations not initialized")
    return await market_status_ops.get_exchange_status()


async def _is_market_open_impl(client) -> bool:
    market_status_ops = getattr(client, "_market_status_ops", None)
    if market_status_ops is None:
        raise KalshiClientError("Market status operations not initialized")
    return await market_status_ops.is_market_open()


def _build_order_payload_impl(_client, order_request: OrderRequest) -> Dict[str, Any]:
    try:
        return build_order_payload(order_request)
    except (ValueError, TypeError) as exc:
        raise KalshiClientError(str(exc)) from exc


def _auth_headers_impl(client, method: str, path: str) -> Dict[str, str]:
    helper = getattr(client, "_auth_helper", None)
    if helper is None:
        raise KalshiClientError("KalshiClient.auth_helper is not initialized")
    return helper.create_auth_headers(method, path)


async def _fetch_order_metadata_impl(client, order_id: str) -> Dict[str, str]:
    order_ops = getattr(client, "_order_ops", None)
    if order_ops is None:
        raise KalshiClientError("Kalshi trade store is not configured")
    metadata_manager = getattr(order_ops, "_metadata_manager", None)
    if metadata_manager is None:
        raise KalshiClientError("Kalshi trade store is not configured")
    return await metadata_manager.fetch_metadata(order_id)


def _parse_order_response_impl(
    client,
    payload: Dict[str, Any],
    trade_rule: Optional[str],
    trade_reason: Optional[str],
) -> OrderResponse:
    response_parser = getattr(client, "_response_parser", None)
    if response_parser is None:
        raise KalshiClientError("Response parser not initialized")
    return response_parser.parse_order_response(payload, trade_rule, trade_reason)


async def _batch_create_orders_impl(client, order_requests: List[OrderRequest]) -> List[BatchOrderResult]:
    order_ops = getattr(client, "_order_ops", None)
    if order_ops is None:
        raise KalshiClientError("Order operations not initialized")
    return await order_ops.batch_create_orders(order_requests)


def _parse_order_fill_impl(client, payload: Dict[str, Any]) -> Dict[str, Any]:
    response_parser = getattr(client, "_response_parser", None)
    if response_parser is None:
        raise KalshiClientError("Response parser not initialized")
    return response_parser.parse_order_fill(payload)


def _unwrap_response(response):
    parent = getattr(response, "_mock_parent", None)
    return parent if parent is not None else response


def _normalise_fill(client, payload: Dict[str, Any]) -> Dict[str, Any]:
    response_parser = getattr(client, "_response_parser", None)
    if response_parser is None:
        raise KalshiClientError("Response parser not initialized")
    return response_parser.normalise_fill(payload)


def bind_client_methods(client_cls, session_getter, session_setter) -> None:
    """Bind session and related properties to client class."""
    client_cls.session = property(session_getter, session_setter)
    client_cls.session_lock = property(_get_session_lock, _set_session_lock)
    setattr(
        client_cls,
        "_session",
        property(lambda self: self.session, lambda self, value: setattr(self, "session", value)),
    )
    setattr(
        client_cls,
        "_session_lock",
        property(
            lambda self: self.session_lock,
            lambda self, value: setattr(self, "session_lock", value),
        ),
    )
    client_cls.initialized = property(_get_initialized, _set_initialized)
    client_cls.trade_store = property(_get_trade_store, _set_trade_store)

    client_cls.initialize = _initialize
    client_cls.close = _close
    client_cls.attach_trade_store = _attach_trade_store
    setattr(client_cls, "_normalise_fill", _normalise_fill)
    client_cls.api_request = _api_request_impl
    setattr(client_cls, "_direct_api_request", _direct_api_request_impl)
    setattr(client_cls, "_raw_api_request", _direct_api_request_impl)
    client_cls.get_portfolio_balance = _get_portfolio_balance_impl
    client_cls.get_portfolio_positions = _get_portfolio_positions_impl
    client_cls.create_order = _create_order_impl
    client_cls.batch_create_orders = _batch_create_orders_impl
    client_cls.cancel_order = _cancel_order_impl
    client_cls.get_order = _get_order_impl
    client_cls.get_fills = _get_fills_impl
    client_cls.get_series = _get_series_impl
    client_cls.get_all_fills = _get_all_fills_impl
    client_cls.get_exchange_status = _get_exchange_status_impl
    client_cls.is_market_open = _is_market_open_impl
    setattr(client_cls, "_build_order_payload", _build_order_payload_impl)
    client_cls.auth_headers = _auth_headers_impl
    setattr(client_cls, "_auth_headers", _auth_headers_impl)
    setattr(client_cls, "_fetch_order_metadata", _fetch_order_metadata_impl)
    setattr(client_cls, "_parse_order_response", _parse_order_response_impl)
    setattr(client_cls, "_parse_order_fill", _parse_order_fill_impl)
