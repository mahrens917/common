from __future__ import annotations

"""
Persistence helpers for P&L snapshots.

Daily summaries and unrealised P&L snapshots are stored alongside trades but
live on separate key spaces. This module keeps the wiring outside the main
TradeStore to make error handling explicit and discoverable.
"""

from datetime import date, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

import orjson

from ...data_models.trade_record import PnLReport
from ..typing import RedisClient, ensure_awaitable
from .errors import TradeStoreError
from .keys import TradeKeyBuilder


class PnLStore:
    """Manage P&L snapshots in Redis."""

    def __init__(
        self,
        redis_provider: Callable[[], Awaitable[RedisClient]],
        *,
        key_builder: TradeKeyBuilder,
        logger,
    ) -> None:
        self._redis_provider = redis_provider
        self._keys = key_builder
        self._logger = logger

    async def store_daily_summary(self, summary: PnLReport) -> bool:
        client = await self._redis_provider()
        summary_data = {
            "report_date": summary.report_date.isoformat(),
            "start_date": summary.start_date.isoformat(),
            "end_date": summary.end_date.isoformat(),
            "total_trades": summary.total_trades,
            "total_cost_cents": summary.total_cost_cents,
            "total_pnl_cents": summary.total_pnl_cents,
            "win_rate": summary.win_rate,
        }
        summary_json = orjson.dumps(summary_data).decode("utf-8")
        key = self._keys.daily_summary(summary.report_date)
        await ensure_awaitable(client.set(key, summary_json))
        self._logger.debug("Stored daily summary for %s", summary.report_date)
        return True

    async def get_daily_summary(self, trade_date: date) -> Optional[Dict[str, Any]]:
        client = await self._redis_provider()
        summary_json = await ensure_awaitable(client.get(self._keys.daily_summary(trade_date)))
        if not summary_json:
            return None
        try:
            return orjson.loads(summary_json)
        except orjson.JSONDecodeError as exc:
            raise TradeStoreError(f"Invalid daily summary JSON for {trade_date}") from exc

    async def store_unrealized_snapshot(self, redis_key: str, data: Dict[str, Any]) -> bool:
        client = await self._redis_provider()
        snapshot = orjson.dumps(data).decode("utf-8")
        await ensure_awaitable(client.set(redis_key, snapshot))
        self._logger.debug("Stored unrealized P&L data: %s", redis_key)
        return True

    async def get_unrealized_snapshot(self, redis_key: str) -> Optional[Dict[str, Any]]:
        client = await self._redis_provider()
        snapshot = await ensure_awaitable(client.get(redis_key))
        if not snapshot:
            return None
        try:
            return orjson.loads(snapshot)
        except orjson.JSONDecodeError as exc:
            raise TradeStoreError(f"Invalid unrealized P&L JSON for {redis_key}") from exc

    async def get_unrealized_history(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        history: List[Dict[str, Any]] = []
        current = start_date
        while current <= end_date:
            snapshot = await self.get_unrealized_snapshot(self._keys.unrealized_pnl(current))
            if snapshot:
                history.append(snapshot)
            current += timedelta(days=1)
        self._logger.debug(
            "Retrieved %s unrealized P&L snapshots for %s to %s",
            len(history),
            start_date,
            end_date,
        )
        return history


__all__ = ["PnLStore"]
