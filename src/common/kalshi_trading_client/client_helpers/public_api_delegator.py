"""Delegate all public API methods."""

from typing import Any, Dict, List, Optional

from ...data_models.trading import OrderRequest, OrderResponse, PortfolioBalance, PortfolioPosition
from .public_api import PublicAPI
from .trade_collection import TradeCollectionManager
from .trade_store_ops import TradeStoreOperations


class PublicAPIDelegator:
    """Delegates all public API methods to helpers."""

    def __init__(self, portfolio, orders, trade_collection, trade_store_manager, private, cancel_order_fn):
        self._portfolio = portfolio
        self._orders = orders
        self._trade_collection = trade_collection
        self._trade_store_manager = trade_store_manager
        self._private = private
        self._cancel_order_fn = cancel_order_fn

    async def get_portfolio_balance(self) -> PortfolioBalance:
        return await PublicAPI.get_portfolio_balance(self._portfolio)

    async def get_portfolio_positions(self) -> List[PortfolioPosition]:
        return await PublicAPI.get_portfolio_positions(self._portfolio)

    async def create_order(self, order_request: OrderRequest) -> OrderResponse:
        return await PublicAPI.create_order(self._orders, order_request)

    async def create_order_with_polling(self, order_request: OrderRequest, timeout_seconds: int = 5) -> OrderResponse:
        return await PublicAPI.create_order_with_polling(
            self._orders,
            order_request,
            timeout_seconds,
            self._cancel_order_fn,
        )

    async def cancel_order(self, order_id: str) -> bool:
        return await PublicAPI.cancel_order(self._orders, order_id)

    async def get_fills(self, order_id: str) -> List[Dict[str, Any]]:
        return await PublicAPI.get_fills(self._orders, order_id)

    async def get_all_fills(
        self,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        ticker: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await PublicAPI.get_all_fills(self._orders, min_ts, max_ts, ticker, cursor)

    async def start_trade_collection(self):
        await TradeCollectionManager.start_collection(self._trade_collection)
        return True

    async def stop_trade_collection(self):
        await TradeCollectionManager.stop_collection(self._trade_collection)
        return False

    async def require_trade_store(self):
        return await TradeStoreOperations.require_trade_store(self._trade_store_manager)
