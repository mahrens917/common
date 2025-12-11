from __future__ import annotations

"""
Aggregate trade queries built on top of the repository primitives.

These helpers keep iteration logic and validation separate from the primary
TradeStore class so unit tests can focus on specific business rules.
"""


from datetime import date, timedelta
from typing import Callable, List

from ...data_models.trade_record import TradeRecord, get_trade_close_date
from .errors import TradeStoreError
from .keys import TradeKeyBuilder
from .records import TradeRecordRepository


class TradeQueryService:
    """High-level queries over stored trades."""

    def __init__(
        self,
        repository: TradeRecordRepository,
        *,
        key_builder: TradeKeyBuilder,
        logger,
        timezone,
        start_date_loader: Callable[[], date],
        timezone_aware_date_loader: Callable[[object], date],
    ) -> None:
        self._repository = repository
        self._keys = key_builder
        self._logger = logger
        self._timezone = timezone
        self._start_date_loader = start_date_loader
        self._timezone_aware_date = timezone_aware_date_loader

    async def trades_by_date_range(self, start_date: date, end_date: date) -> List[TradeRecord]:
        minimum_trade_date = self._start_date_loader()
        if end_date < minimum_trade_date:
            if start_date < minimum_trade_date:
                return []
            raise TradeStoreError(f"Requested end date {end_date} predates supported history ({minimum_trade_date})")
        if start_date < minimum_trade_date:
            raise TradeStoreError(f"Requested start date {start_date} predates supported history ({minimum_trade_date})")

        trades: List[TradeRecord] = []
        current = start_date
        while current <= end_date:
            order_ids = await self._repository.load_all_for_date(current)
            for order_id in order_ids:
                trade = await self._repository.get(current, order_id)
                if trade is None:
                    raise TradeStoreError(f"Trade {order_id} expected for {current} but payload is missing")
                trades.append(trade)
            current += timedelta(days=1)
        return trades

    async def trades_by_station(self, station: str) -> List[TradeRecord]:
        order_ids = await self._repository.load_index(self._keys.station(station))
        return await self._collect_trades_by_id(order_ids, context=f"station {station}")

    async def trades_by_rule(self, rule: str) -> List[TradeRecord]:
        order_ids = await self._repository.load_index(self._keys.rule(rule))
        return await self._collect_trades_by_id(order_ids, context=f"rule {rule}")

    async def trades_closed_today(self) -> List[TradeRecord]:
        today = self._timezone_aware_date(self._timezone)
        yesterday = today - timedelta(days=1)
        today_trades = await self.trades_by_date_range(today, today)
        yesterday_trades = await self.trades_by_date_range(yesterday, yesterday)

        closed_today = [trade for trade in today_trades + yesterday_trades if get_trade_close_date(trade) == today]
        self._logger.debug("Found %s trades closing on %s", len(closed_today), today)
        return closed_today

    async def trades_closed_yesterday(self) -> List[TradeRecord]:
        today = self._timezone_aware_date(self._timezone)
        yesterday = today - timedelta(days=1)
        trades = await self.trades_by_date_range(yesterday - timedelta(days=1), yesterday)
        closed_yesterday = [trade for trade in trades if get_trade_close_date(trade) == yesterday]
        self._logger.debug("Found %s trades closing on %s", len(closed_yesterday), yesterday)
        return closed_yesterday

    async def unrealized_trades_for_date(self, target_date: date) -> List[TradeRecord]:
        trades = await self.trades_by_date_range(target_date, target_date)
        self._logger.debug("Found %s trades for %s", len(trades), target_date)
        return trades

    async def _collect_trades_by_id(self, order_ids: List[str], *, context: str) -> List[TradeRecord]:
        trades: List[TradeRecord] = []
        for order_id in order_ids:
            trade = await self._repository.get_by_order_id(order_id)
            if trade is None:
                raise TradeStoreError(f"Trade {order_id} expected for {context} but not found")
            trades.append(trade)
        return trades


__all__ = ["TradeQueryService"]
