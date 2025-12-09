from __future__ import annotations

"""Portfolio operations (balance, positions)."""


from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from src.common.data_models.trading import PortfolioBalance, PortfolioPosition

    from ..services import PortfolioService


class PortfolioOperations:
    """Handles portfolio-related operations."""

    @staticmethod
    async def get_balance(portfolio_service: PortfolioService) -> PortfolioBalance:
        """Get current portfolio balance."""
        return await portfolio_service.get_balance()

    @staticmethod
    async def get_positions(portfolio_service: PortfolioService) -> List[PortfolioPosition]:
        """Get current portfolio positions."""
        return await portfolio_service.get_positions()
