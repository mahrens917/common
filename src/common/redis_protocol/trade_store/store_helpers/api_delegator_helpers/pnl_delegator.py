"""P&L operations delegation"""

from datetime import date
from typing import Any, Dict, Optional

from .....data_models.trade_record import PnLReport


class PnLDelegator:
    """Delegates P&L operations"""

    def __init__(self, pnl, executor):
        """
        Initialize P&L delegator

        Args:
            pnl: PnLManager instance
            executor: Executor for Redis guard operations
        """
        self._pnl = pnl
        self._executor = executor

    async def store_daily_summary(self, summary: PnLReport) -> bool:
        """Store daily P&L summary"""
        return await self._executor.run_with_redis_guard("store_daily_summary", lambda: self._pnl.store_daily_summary(summary))

    async def get_daily_summary(self, trade_date: date) -> Optional[Dict[str, Any]]:
        """Get daily P&L summary"""
        return await self._executor.run_with_redis_guard("get_daily_summary", lambda: self._pnl.get_daily_summary(trade_date))

    async def store_unrealized_pnl_data(self, redis_key: str, data: Dict[str, Any]) -> bool:
        """Store unrealized P&L snapshot"""
        return await self._executor.run_with_redis_guard(
            "store_unrealized_pnl_data",
            lambda: self._pnl.store_unrealized_snapshot(redis_key, data),
        )

    async def get_unrealized_pnl_data(self, redis_key: str) -> Optional[Dict[str, Any]]:
        """Get unrealized P&L snapshot"""
        return await self._executor.run_with_redis_guard("get_unrealized_pnl_data", lambda: self._pnl.get_unrealized_snapshot(redis_key))

    async def get_unrealized_pnl_history(self, start_date: date, end_date: date) -> list[Dict[str, Any]]:
        """Get unrealized P&L history"""
        return await self._executor.run_with_redis_guard(
            "get_unrealized_pnl_history",
            lambda: self._pnl.get_unrealized_history(start_date, end_date),
        )
