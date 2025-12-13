"""Shared Kalshi client lazy initialization helpers."""

from __future__ import annotations

import asyncio
from typing import Optional

from src.kalshi.api.client import KalshiClient


class KalshiClientMixin:
    _kalshi_client: Optional[KalshiClient]
    _kalshi_client_lock: asyncio.Lock

    async def _get_kalshi_client(self) -> KalshiClient:
        async with self._kalshi_client_lock:
            if self._kalshi_client is None:
                self._kalshi_client = KalshiClient()
            return self._kalshi_client


__all__ = ["KalshiClientMixin"]
