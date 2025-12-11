from __future__ import annotations

"""Adapters for delivering Kalshi trade notifications."""

import asyncio
import urllib.error
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type

from ..data_models.trading import OrderRequest
from ..trading_exceptions import KalshiTradeNotificationError


class TradeNotifierAdapter:
    """Thin wrapper around the global trade notifier to keep KalshiTradingClient lean."""

    def __init__(
        self,
        *,
        notifier_supplier: Optional[Callable[[], Any]] = None,
        notification_error_types: Optional[Iterable[Type[Exception]]] = None,
    ) -> None:
        if notifier_supplier is None:
            try:
                from kalshi.notifications.trade_notifier import (  # type: ignore[import]
                    TradeNotificationError,
                    get_trade_notifier,
                )
                notifier_supplier = get_trade_notifier
                error_types = tuple(notification_error_types or (TradeNotificationError,))
            except ImportError:
                notifier_supplier = None
                error_types = tuple(notification_error_types or ())
        else:
            error_types = tuple(notification_error_types or ())

        self._notifier_supplier = notifier_supplier
        self._notification_error_types: Tuple[Type[Exception], ...] = error_types

    async def notify_order_error(
        self,
        order_request: OrderRequest,
        error: Exception,
        *,
        operation_name: str,
        notifier_error_message: str,
    ) -> None:
        """Propagate order errors to the notifier with consistent error handling."""

        try:
            trade_notifier = self._notifier_supplier()
        except RuntimeError as exc:
            raise KalshiTradeNotificationError(
                "Trade notifier unavailable",
                order_id=order_request.client_order_id,
                operation_name=operation_name,
            ) from exc

        if not trade_notifier:
            return

        order_data: Dict[str, Any] = {
            "ticker": order_request.ticker,
            "action": order_request.action.value,
            "side": order_request.side.value,
            "yes_price_cents": order_request.yes_price_cents,
            "count": order_request.count,
            "client_order_id": order_request.client_order_id,
        }

        error_types = self._notification_error_types
        if not error_types:
            try:
                from kalshi.notifications.trade_notifier import TradeNotificationError  # type: ignore[import]
                error_types = (TradeNotificationError,)
            except ImportError:
                error_types = (RuntimeError,)

        try:
            await trade_notifier.send_order_error_notification(order_data, error)
        except error_types as exc:
            raise KalshiTradeNotificationError(
                notifier_error_message,
                order_id=order_request.client_order_id,
                operation_name=operation_name,
            ) from exc
        except (
            RuntimeError,
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            urllib.error.URLError,
        ) as exc:
            raise KalshiTradeNotificationError(
                "Trade notifier unavailable",
                order_id=order_request.client_order_id,
                operation_name=operation_name,
            ) from exc


__all__ = ["TradeNotifierAdapter"]
