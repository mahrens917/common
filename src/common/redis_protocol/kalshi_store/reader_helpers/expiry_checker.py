"""
Expiry Checker - Expiry validation and checking

Handles expiry date validation, settlement checking, and time comparisons.
"""

import logging
from datetime import datetime

from redis.asyncio import Redis

from ....time_utils import get_current_utc
from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from .close_time_parser import CloseTimeParser

logger = logging.getLogger(__name__)


class ExpiryChecker:
    """Check market expiry and settlement status"""

    def __init__(self, logger_instance: logging.Logger):
        self.logger = logger_instance

    async def is_market_expired(self, redis: Redis, market_key: str, market_ticker: str) -> bool:
        """Determine whether the given market has already expired."""
        try:
            market_data = await ensure_awaitable(redis.hgetall(market_key))
            if not market_data:
                return False

            current_time = get_current_utc()
            close_time_raw = market_data.get("close_time")
            close_datetime = CloseTimeParser.parse_close_time_from_field(close_time_raw)

            if close_datetime and close_datetime < current_time:
                close_time_str = CloseTimeParser.decode_close_time_string(close_time_raw)
                self.logger.info("Market %s expired: close_time %s < current time", market_ticker, close_time_str)
                return True
        except REDIS_ERRORS as exc:
            self.logger.error(
                "Redis error checking if market %s is expired: %s",
                market_ticker,
                exc,
                exc_info=True,
            )
            return False
        else:
            return False

    async def is_market_settled(self, redis: Redis, market_key: str, market_ticker: str) -> bool:
        """Determine whether the given market has been settled."""
        try:
            market_data = await ensure_awaitable(redis.hgetall(market_key))
            if not market_data:
                return False

            raw_close_time = market_data.get("close_time")
            close_time_str = CloseTimeParser.decode_close_time_string(raw_close_time)
            if not close_time_str:
                self.logger.debug("Market %s has no close_time - not settled", market_ticker)
                return False

            close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
            current_time = get_current_utc()
            is_settled = current_time > close_time

            log_template = (
                "Market %s is settled: close_time=%s, current_time=%s"
                if is_settled
                else "Market %s not settled: close_time=%s, current_time=%s"
            )
            log_fn = self.logger.info if is_settled else self.logger.debug
            log_fn(log_template, market_ticker, close_time_str, current_time)
        except REDIS_ERRORS as exc:
            self.logger.error(
                "Redis error checking if market %s is settled: %s",
                market_ticker,
                exc,
                exc_info=True,
            )
            return False
        else:
            return is_settled
