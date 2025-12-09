"""Trade query operations delegation"""

from datetime import date

from .....data_models.trade_record import TradeRecord


class QueryDelegator:
    """Delegates trade query operations"""

    def __init__(self, queries, executor):
        """
        Initialize query delegator

        Args:
            queries: TradeStoreQueries instance
            executor: Executor for Redis guard operations
        """
        self._queries = queries
        self._executor = executor

    async def get_trades_by_date_range(self, start_date: date, end_date: date) -> list[TradeRecord]:
        """Get trades within a date range"""
        return await self._executor.run_with_redis_guard(
            "get_trades_by_date_range",
            lambda: self._queries.trades_by_date_range(start_date, end_date),
        )

    async def get_trades_by_station(self, station: str) -> list[TradeRecord]:
        """Get trades for a specific weather station"""
        return await self._executor.run_with_redis_guard(
            "get_trades_by_station", lambda: self._queries.trades_by_station(station)
        )

    async def get_trades_by_rule(self, rule: str) -> list[TradeRecord]:
        """Get trades for a specific trading rule"""
        return await self._executor.run_with_redis_guard(
            "get_trades_by_rule", lambda: self._queries.trades_by_rule(rule)
        )

    async def get_trades_closed_today(self) -> list[TradeRecord]:
        """Get trades closed today"""
        return await self._executor.run_with_redis_guard(
            "get_trades_closed_today", self._queries.trades_closed_today
        )

    async def get_trades_closed_yesterday(self) -> list[TradeRecord]:
        """Get trades closed yesterday"""
        return await self._executor.run_with_redis_guard(
            "get_trades_closed_yesterday", self._queries.trades_closed_yesterday
        )

    async def get_unrealized_trades_for_date(self, target_date: date) -> list[TradeRecord]:
        """Get unrealized trades for a specific date"""
        return await self._executor.run_with_redis_guard(
            "get_unrealized_trades_for_date",
            lambda: self._queries.unrealized_trades_for_date(target_date),
        )
