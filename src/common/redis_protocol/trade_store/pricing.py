from __future__ import annotations

"""
Helpers for updating trade pricing metadata.

The updater reuses the repository abstractions to keep tests focused on price
update rules while ensuring Redis writes remain centralised.
"""


from datetime import date, datetime, timedelta
from typing import Callable

from ...data_models.trade_record import TradeRecord
from .errors import TradeStoreError
from .records import TradeRecordRepository


class TradePriceUpdater:
    """Apply pricing updates across recent trades for a market ticker."""

    def __init__(
        self,
        repository: TradeRecordRepository,
        *,
        timezone,
        timezone_aware_date_loader: Callable[[object], date],
        current_time_provider: Callable[[], datetime],
        logger,
    ) -> None:
        self._repository = repository
        self._timezone = timezone
        self._timezone_date = timezone_aware_date_loader
        self._now = current_time_provider
        self._logger = logger

    async def update_market_prices(
        self,
        market_ticker: str,
        *,
        yes_bid: float,
        yes_ask: float,
        lookback_days: int = 7,
    ) -> int:
        if lookback_days <= 0:
            raise TypeError("lookback_days must be positive")

        today = self._timezone_date(self._timezone)
        updated_count = 0

        for days_back in range(lookback_days):
            search_date = today - timedelta(days=days_back)
            order_ids = await self._repository.load_all_for_date(search_date)
            for order_id in order_ids:
                trade = await self._repository.get(search_date, order_id)
                if trade is None:
                    raise TradeStoreError(f"Trade {order_id} expected for {search_date} but payload missing")
                if trade.market_ticker != market_ticker:
                    continue
                await self._apply_price_update(trade, yes_bid=yes_bid, yes_ask=yes_ask)
                updated_count += 1

        self._logger.debug("Updated prices for %s trades in market %s", updated_count, market_ticker)
        return updated_count

    async def _apply_price_update(
        self,
        trade: TradeRecord,
        *,
        yes_bid: float,
        yes_ask: float,
    ) -> None:
        trade.last_yes_bid = yes_bid
        trade.last_yes_ask = yes_ask
        trade.last_price_update = self._now()
        await self._repository.save_without_reindex(trade)


__all__ = ["TradePriceUpdater"]
