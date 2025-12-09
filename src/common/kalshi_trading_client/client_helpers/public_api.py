from __future__ import annotations

"""Public API methods delegation."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from src.common.data_models.trading import (
        OrderRequest,
        OrderResponse,
        PortfolioBalance,
        PortfolioPosition,
    )

    from ..services import OrderService, PortfolioService


class PublicAPI:
    """Delegates public API methods to services."""

    @staticmethod
    async def get_portfolio_balance(portfolio_service: PortfolioService) -> PortfolioBalance:
        """Get portfolio balance."""
        from .portfolio_operations import PortfolioOperations

        return await PortfolioOperations.get_balance(portfolio_service)

    @staticmethod
    async def get_portfolio_positions(
        portfolio_service: PortfolioService,
    ) -> List[PortfolioPosition]:
        """Get portfolio positions."""
        from .portfolio_operations import PortfolioOperations

        return await PortfolioOperations.get_positions(portfolio_service)

    @staticmethod
    async def create_order(
        order_service: OrderService, order_request: OrderRequest
    ) -> OrderResponse:
        """Create an order."""
        from .order_operations import OrderOperations

        return await OrderOperations.create_order(order_service, order_request)

    @staticmethod
    async def create_order_with_polling(
        order_service: OrderService,
        order_request: OrderRequest,
        timeout_seconds: int,
        cancel_order_func,
    ) -> OrderResponse:
        """Create order with polling."""
        from .order_operations import OrderOperations

        return await OrderOperations.create_order_with_polling(
            order_service,
            order_request,
            timeout_seconds,
            cancel_order_func,
        )

    @staticmethod
    async def cancel_order(order_service: OrderService, order_id: str) -> bool:
        """Cancel an order."""
        from .order_operations import OrderOperations

        return await OrderOperations.cancel_order(order_service, order_id)

    @staticmethod
    async def get_fills(order_service: OrderService, order_id: str) -> List[Dict[str, Any]]:
        """Get fills for an order."""
        from .order_operations import OrderOperations

        return await OrderOperations.get_fills(order_service, order_id)

    @staticmethod
    async def get_all_fills(
        order_service: OrderService,
        min_ts: Optional[int],
        max_ts: Optional[int],
        ticker: Optional[str],
        cursor: Optional[str],
    ) -> Dict[str, Any]:
        """Get all fills with filters."""
        from .order_operations import OrderOperations

        return await OrderOperations.get_all_fills(order_service, min_ts, max_ts, ticker, cursor)
