"""Shared error tuple for PnL helper data access operations."""

from __future__ import annotations

import asyncio
from typing import Tuple

from redis.exceptions import RedisError

from ..redis_protocol.trade_store import TradeStoreError
from ..redis_utils import RedisOperationError

DATA_ACCESS_ERRORS: Tuple[type[BaseException], ...] = (
    TradeStoreError,
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
)
