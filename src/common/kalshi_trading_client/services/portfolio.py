from __future__ import annotations

"""
Portfolio helpers for the Kalshi trading client.
"""


import logging
from typing import List

from ...data_models.trading import PortfolioBalance, PortfolioPosition
from ...trading_exceptions import KalshiAPIError
from ..constants import CLIENT_API_ERRORS

logger = logging.getLogger(__name__)


class PortfolioService:
    """Fetch portfolio balances and open positions."""

    def __init__(self, *, kalshi_client) -> None:
        self._client = kalshi_client

    async def get_balance(self) -> PortfolioBalance:
        operation_name = "get_portfolio_balance"
        logger.info(f"[{operation_name}] Retrieving portfolio balance")

        try:
            portfolio_balance = await self._client.get_portfolio_balance()
            logger.info(
                f"[{operation_name}] Retrieved balance: ${portfolio_balance.balance_cents/100:.2f}"
            )
        except CLIENT_API_ERRORS as exc:
            logger.exception(
                "[%s] Error retrieving portfolio balance (%s)",
                operation_name,
                type(exc).__name__,
            )
            raise KalshiAPIError(
                f"Failed to retrieve portfolio balance", operation_name=operation_name
            ) from exc
        else:
            return portfolio_balance

    async def get_positions(self) -> List[PortfolioPosition]:
        operation_name = "get_portfolio_positions"
        logger.info(f"[{operation_name}] Retrieving portfolio positions")

        try:
            positions = await self._client.get_portfolio_positions()
            logger.info(f"[{operation_name}] Retrieved {len(positions)} positions")
        except CLIENT_API_ERRORS as exc:
            logger.exception(
                "[%s] Error retrieving portfolio positions (%s)",
                operation_name,
                type(exc).__name__,
            )
            raise KalshiAPIError(
                f"Failed to retrieve portfolio positions", operation_name=operation_name
            ) from exc
        else:
            return positions


__all__ = ["PortfolioService"]
