"""API methods mixin for KalshiTradingClient."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..backoff_manager_helpers import BackoffType
from .client_helpers.backoff_retry import with_backoff_retry

if TYPE_CHECKING:
    from ..data_models.trading import (
        BatchOrderResult,
        OrderRequest,
        OrderResponse,
        PortfolioBalance,
        PortfolioPosition,
    )
    from ..redis_protocol.trade_store import TradeStore

_logger = logging.getLogger(__name__)


class KalshiTradingClientAPIMixin:
    """Mixin for public API methods."""

    _api: Any
    is_running: bool
    trade_store: Any
    backoff_manager: Any
    service_name: str

    async def get_portfolio_balance(self) -> PortfolioBalance:
        backoff = getattr(self, "backoff_manager", None)
        if backoff is not None:
            return await with_backoff_retry(
                self._api.get_portfolio_balance,
                backoff_manager=backoff,
                service_name=self.service_name,
                backoff_type=BackoffType.NETWORK_FAILURE,
                context="get_portfolio_balance",
            )
        return await self._api.get_portfolio_balance()

    async def get_portfolio_positions(self) -> List[PortfolioPosition]:
        return await self._api.get_portfolio_positions()

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        return await self._api.create_order(order_request)

    async def batch_create_orders(self, order_requests: list["OrderRequest"]) -> list["BatchOrderResult"]:
        return await self._api.batch_create_orders(order_requests)

    async def cancel_order(self, order_id: str) -> bool:
        return await self._api.cancel_order(order_id)

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        return await self._api.get_fills(order_id)

    async def get_all_fills(
        self,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        ticker: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._api.get_all_fills(min_ts, max_ts, ticker, cursor)

    async def start_trade_collection(self) -> bool:
        store_getter = getattr(self, "_get_trade_store", None)
        if store_getter is not None:
            try:
                await store_getter()
            except (AttributeError, RuntimeError, ValueError, TypeError) as exc:
                raise ValueError("Trade store required for trade collection") from exc
        elif not hasattr(self, "trade_store") or self.trade_store is None:
            raise ValueError("Trade store required for trade collection")
        result = await self._api.start_trade_collection()
        self.is_running = result
        return result

    async def stop_trade_collection(self) -> bool:
        result = await self._api.stop_trade_collection()
        self.is_running = result
        return result

    async def require_trade_store(self) -> TradeStore:
        store = await self._api.require_trade_store()
        self.trade_store = store
        return store


class KalshiTradingClientTradeStoreMixin:
    """Mixin for trade store operations."""

    _trade_store_manager: Any

    async def get_trade_store(self) -> TradeStore:
        from .client_helpers import TradeStoreOperations

        return await TradeStoreOperations.get_trade_store(self._trade_store_manager)

    async def maybe_get_trade_store(self) -> Optional[TradeStore]:
        from .client_helpers import TradeStoreOperations

        return await TradeStoreOperations.maybe_get_trade_store(self._trade_store_manager)

    async def ensure_trade_store(self, *, create: bool = True) -> Optional[TradeStore]:
        from .client_helpers import TradeStoreOperations

        return await TradeStoreOperations.ensure_trade_store(self._trade_store_manager, create=create)


__all__ = [
    "KalshiTradingClientAPIMixin",
    "KalshiTradingClientTradeStoreMixin",
]
