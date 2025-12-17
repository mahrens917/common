from __future__ import annotations

"""
Shared error classifications for Kalshi trading client services.
"""


import asyncio
import urllib.error

from common.kalshi_api.client import KalshiClientError

from ..trading_exceptions import KalshiTradingError

CLIENT_API_ERRORS = (
    KalshiClientError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)

CLEANUP_ERRORS = CLIENT_API_ERRORS + (KalshiTradingError,)

TELEGRAM_ALERT_ERRORS = (
    RuntimeError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    urllib.error.URLError,
    OSError,
)

__all__ = ["CLIENT_API_ERRORS", "CLEANUP_ERRORS", "TELEGRAM_ALERT_ERRORS"]
