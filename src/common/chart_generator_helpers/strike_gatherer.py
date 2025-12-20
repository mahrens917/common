from __future__ import annotations

"""Helper for gathering strikes from Redis patterns"""

import logging
from datetime import date
from typing import Any, Callable, Sequence

from common.redis_protocol.typing import RedisClient

from .config import StrikeCollectionContext

logger = logging.getLogger("src.monitor.chart_generator")


class StrikeGatherer:
    """Gathers strikes from Redis key patterns"""

    def __init__(self, *, schema, hash_decoder, strike_accumulator, expiration_validator):
        self.schema = schema
        self.hash_decoder = hash_decoder
        self.strike_accumulator = strike_accumulator
        self.expiration_validator = expiration_validator

    async def gather_strikes_for_tokens(
        self: StrikeGatherer,
        *,
        redis_client: RedisClient,
        tokens: Sequence[str],
        parse_fn: Callable[[str], Any],
        today_et: date,
        et_timezone,
        today_market_date: str,
    ) -> tuple[set[float], bool]:
        strikes: set[float] = set()
        primary_found = False
        for token in tokens:
            normalized_token = token.lower()
            pattern = f"{self.schema.kalshi_weather_prefix}:*{normalized_token}*"
            async for market_key in redis_client.scan_iter(match=pattern, count=100):
                key_str = market_key.decode("utf-8") if isinstance(market_key, bytes) else str(market_key)
                context = StrikeCollectionContext(
                    redis_client=redis_client,
                    key_str=key_str,
                    parse_fn=parse_fn,
                    today_et=today_et,
                    et_timezone=et_timezone,
                    today_market_date=today_market_date,
                    strikes=strikes,
                )
                added = await self._collect_strikes_from_key(context=context)
                if added:
                    primary_found = True
        return strikes, primary_found

    async def collect_strikes_from_key_list(
        self: StrikeGatherer,
        *,
        redis_client: RedisClient,
        key_candidates: Sequence[Any],
        parse_fn: Callable[[str], Any],
        today_et: date,
        et_timezone,
        today_market_date: str,
    ) -> set[float]:
        strikes: set[float] = set()
        for market_key in key_candidates:
            key_str = market_key.decode("utf-8") if isinstance(market_key, bytes) else str(market_key)
            context = StrikeCollectionContext(
                redis_client=redis_client,
                key_str=key_str,
                parse_fn=parse_fn,
                today_et=today_et,
                et_timezone=et_timezone,
                today_market_date=today_market_date,
                strikes=strikes,
            )
            await self._collect_strikes_from_key(context=context)
        return strikes

    async def _collect_strikes_from_key(
        self: StrikeGatherer,
        *,
        context: StrikeCollectionContext,
    ) -> bool:
        if ":trading_signal" in context.key_str or ":position_state" in context.key_str:
            return False
        try:
            ticker = context.parse_fn(context.key_str).ticker
        except ValueError:
            return False
        from common.redis_protocol.typing import ensure_awaitable

        market_data = await ensure_awaitable(context.redis_client.hgetall(context.key_str))
        if not market_data:
            return False
        decoded = self.hash_decoder.decode_weather_market_hash(market_data)
        if not self.expiration_validator.market_expires_today(
            decoded, context.today_et, context.et_timezone, ticker, context.today_market_date
        ):
            return False
        before = len(context.strikes)
        strike_type, floor_strike, cap_strike = self.hash_decoder.extract_strike_info(decoded)
        self.strike_accumulator.accumulate_strike_values(strike_type, floor_strike, cap_strike, context.strikes)
        return len(context.strikes) > before
