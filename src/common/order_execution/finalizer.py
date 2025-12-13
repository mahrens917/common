from __future__ import annotations

from common.truthy import pick_if

"""
Trade finalisation helpers for the Kalshi trading client.

The finaliser coordinates trade persistence and downstream notifications once fills have
been reconciled. Separating this logic keeps the trading client orchestration focused on
control flow while allowing targeted unit tests for storage and notification edge cases.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol

from ..data_models.trade_record import TradeRecord, TradeSide
from ..data_models.trading import OrderRequest, OrderResponse, OrderSide
from ..redis_protocol.trade_store import TradeStore
from ..time_utils import get_current_utc
from ..trading_exceptions import KalshiTradeNotificationError, KalshiTradePersistenceError
from .polling import PollingOutcome

logger = logging.getLogger(__name__)


class NotifierProtocol(Protocol):
    async def send_order_executed_notification(
        self,
        order_data: Dict[str, Any],
        response_data: Dict[str, Any],
        kalshi_client,
    ) -> None: ...


TradeStoreProvider = Callable[[], Awaitable[TradeStore]]
ContextResolver = Callable[[str], tuple[str, Optional[str]]]
NotifierSupplier = Callable[[], Optional[NotifierProtocol]]


class TradeFinalizer:
    """Persist executed trades and dispatch notifications once fills are reconciled."""

    def __init__(
        self,
        trade_store_provider: TradeStoreProvider,
        context_resolver: ContextResolver,
        notifier_supplier: NotifierSupplier,
        *,
        kalshi_client,
        operation_name: str = "create_order_with_polling",
    ) -> None:
        self._trade_store_provider = trade_store_provider
        self._context_resolver = context_resolver
        self._notifier_supplier = notifier_supplier
        self._kalshi_client = kalshi_client
        self._operation_name = operation_name

    async def finalize(
        self,
        order_request: OrderRequest,
        order_response: OrderResponse,
        outcome: PollingOutcome,
    ) -> None:
        await _finalize(self, order_request, order_response, outcome)


async def _finalize(
    self,
    order_request: OrderRequest,
    order_response: OrderResponse,
    outcome: PollingOutcome,
) -> None:
    trade_store = await self._trade_store_provider()
    ticker = order_request.ticker
    order_id = order_response.order_id
    _validate_order_metadata(order_request, order_response, ticker, order_id, self._operation_name)
    market_category, weather_station = self._context_resolver(ticker)
    trade_record = _build_trade_record(
        order_request=order_request,
        order_response=order_response,
        outcome=outcome,
        market_category=market_category,
        weather_station=str() if weather_station is None else weather_station,
        trade_timestamp=get_current_utc(),
    )
    await _store_trade(trade_store, trade_record, ticker, order_id, outcome, self._operation_name)
    notifier = self._notifier_supplier()
    if notifier is None:
        return
    await _send_notification(
        notifier,
        order_request,
        order_response,
        self._kalshi_client,
        order_id,
        self._operation_name,
    )


def _validate_order_metadata(
    order_request: OrderRequest,
    order_response: OrderResponse,
    ticker: str,
    order_id: str,
    operation_name: str,
) -> None:
    trade_rule = getattr(order_request, "trade_rule", None)
    trade_reason = getattr(order_request, "trade_reason", None)
    if not trade_rule:
        raise KalshiTradePersistenceError(
            "Order request missing trade_rule metadata",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )
    if not trade_reason:
        raise KalshiTradePersistenceError(
            "Order request missing trade_reason metadata",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )
    if order_response.fees_cents is None:
        raise KalshiTradePersistenceError(
            "Order response missing fees_cents",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        )


async def _store_trade(
    trade_store: TradeStore,
    trade_record,
    ticker: str,
    order_id: str,
    outcome: PollingOutcome,
    operation_name: str,
) -> None:
    try:
        await trade_store.store_trade(trade_record)
        logger.info(
            "[%s] Stored trade immediately in trade store: order_id=%s quantity=%s",
            operation_name,
            order_id,
            outcome.total_filled,
        )
    except (RuntimeError, ValueError, TypeError, KeyError) as exc:  # policy_guard: allow-silent-handler
        raise KalshiTradePersistenceError(
            f"Failed to store trade: {exc}",
            order_id=order_id,
            ticker=ticker,
            operation_name=operation_name,
        ) from exc


async def _send_notification(
    notifier: NotifierProtocol,
    order_request: OrderRequest,
    order_response: OrderResponse,
    kalshi_client,
    order_id: str,
    operation_name: str,
) -> None:
    order_data = _build_order_data_payload(order_request, order_response)
    response_payload = _build_response_data_payload(order_response)
    try:
        await notifier.send_order_executed_notification(order_data, response_payload, kalshi_client)
        logger.info("[%s] Trade notification dispatched for order %s", operation_name, order_id)
    except (RuntimeError, ConnectionError, TimeoutError, asyncio.TimeoutError, OSError) as exc:  # policy_guard: allow-silent-handler
        raise KalshiTradeNotificationError(
            f"Trade notification failed: {exc}",
            order_id=order_id,
            operation_name=operation_name,
        ) from exc


def _build_order_data_payload(order_request: OrderRequest, order_response: OrderResponse) -> Dict[str, object]:
    filled_count = order_response.filled_count
    if filled_count is None:
        filled_count = int()
    remaining_count = order_response.remaining_count
    if remaining_count is None:
        remaining_count = int()
    total_from_response = filled_count + remaining_count
    contract_count = total_from_response if total_from_response else order_request.count
    yes_price_cents = order_request.yes_price_cents
    if yes_price_cents is None:
        yes_price_cents = int()
    return {
        "ticker": order_request.ticker,
        "action": order_request.action.value,
        "side": order_request.side.value,
        "order_type": order_request.order_type.value,
        "count": contract_count,
        "client_order_id": order_request.client_order_id,
        "trade_rule": order_request.trade_rule,
        "trade_reason": order_request.trade_reason,
        "yes_price_cents": yes_price_cents,
        "time_in_force": order_request.time_in_force.value,
        "fees_cents": order_response.fees_cents,
        "order_id": order_response.order_id,
    }


def _build_response_data_payload(order_response: OrderResponse) -> Dict[str, object]:
    timestamp = order_response.timestamp
    assert timestamp is not None, "Order response timestamp must be present"
    timestamp_str = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    average_fill_price_cents = order_response.average_fill_price_cents
    if average_fill_price_cents is None:
        average_fill_price_cents = int()
    return {
        "order_id": order_response.order_id,
        "client_order_id": order_response.client_order_id,
        "ticker": order_response.ticker,
        "status": order_response.status.value,
        "action": order_response.action.value,
        "side": order_response.side.value,
        "order_type": order_response.order_type.value,
        "filled_count": order_response.filled_count,
        "remaining_count": order_response.remaining_count,
        "average_fill_price_cents": average_fill_price_cents,
        "fees_cents": order_response.fees_cents,
        "timestamp": timestamp_str,
        "trade_rule": order_response.trade_rule,
        "trade_reason": order_response.trade_reason,
        "fills": [
            {
                "count": fill.count,
                "side": order_response.side.value,
                "timestamp": fill.timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                **pick_if(
                    order_response.side == OrderSide.YES, lambda: {"yes_price": fill.price_cents}, lambda: {"no_price": fill.price_cents}
                ),
            }
            for fill in (order_response.fills if order_response.fills is not None else list())
        ],
    }


def _build_trade_record(
    *,
    order_request: OrderRequest,
    order_response: OrderResponse,
    outcome: PollingOutcome,
    market_category: str,
    weather_station: str,
    trade_timestamp,
) -> TradeRecord:
    quantity = max(outcome.total_filled, 0)
    price_cents = outcome.average_price_cents
    if price_cents is None:
        price_cents = order_response.average_fill_price_cents
    if price_cents is None:
        price_cents = int()
    fee_cents = order_response.fees_cents
    if fee_cents is None:
        fee_cents = int()
    cost_cents = price_cents * quantity + fee_cents
    trade_side = TradeSide.YES if order_response.side.value == "yes" else TradeSide.NO
    trade_rule = order_response.trade_rule if order_response.trade_rule else order_request.trade_rule
    trade_reason = order_response.trade_reason if order_response.trade_reason else order_request.trade_reason
    resolved_weather_station = None if not weather_station else weather_station
    return TradeRecord(
        order_id=order_response.order_id,
        market_ticker=order_request.ticker,
        trade_timestamp=trade_timestamp,
        trade_side=trade_side,
        quantity=quantity,
        price_cents=price_cents,
        fee_cents=fee_cents,
        cost_cents=cost_cents,
        market_category=market_category,
        trade_rule=trade_rule,
        trade_reason=trade_reason,
        weather_station=resolved_weather_station,
    )
