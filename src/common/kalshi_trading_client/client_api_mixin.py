"""API methods mixin for KalshiTradingClient."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..data_models.trading import (
        OrderRequest,
        OrderResponse,
        PortfolioBalance,
        PortfolioPosition,
    )
    from ..redis_protocol.trade_store import TradeStore


class KalshiTradingClientAPIMixin:
    """Mixin for public API methods."""

    _api: Any
    is_running: bool
    trade_store: Any

    async def get_portfolio_balance(self) -> PortfolioBalance:
        return await self._api.get_portfolio_balance()

    async def get_portfolio_positions(self) -> List[PortfolioPosition]:
        return await self._api.get_portfolio_positions()

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        return await self._api.create_order(order_request)

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

        return await TradeStoreOperations.ensure_trade_store(
            self._trade_store_manager, create=create
        )


__all__ = [
    "KalshiTradingClientAPIMixin",
    "KalshiTradingClientTradeStoreMixin",
]
