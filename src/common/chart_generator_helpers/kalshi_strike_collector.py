from __future__ import annotations

"""Helper for collecting Kalshi strikes from Redis"""

import logging
import sys
from typing import List, Optional

from common.config.redis_schema import get_schema_config
from common.redis_protocol.typing import RedisClient
from common.redis_schema import parse_kalshi_market_key

from .market_expiration_validator import MarketExpirationValidator
from .market_hash_decoder import MarketHashDecoder
from .strike_accumulator import StrikeAccumulator
from .strike_gatherer import StrikeGatherer

logger = logging.getLogger("src.monitor.chart_generator")


class KalshiStrikeCollector:
    """Collects Kalshi temperature strikes for weather stations"""

    def __init__(self):
        self.schema = get_schema_config()
        self.hash_decoder = MarketHashDecoder()
        self.strike_accumulator = StrikeAccumulator()
        self.expiration_validator = MarketExpirationValidator()
        self.gatherer = StrikeGatherer(
            schema=self.schema,
            hash_decoder=self.hash_decoder,
            strike_accumulator=self.strike_accumulator,
            expiration_validator=self.expiration_validator,
        )

    async def get_kalshi_strikes_for_station(
        self: KalshiStrikeCollector,
        redis_client: RedisClient,
        station_icao: str,
        city_tokens: List[str],
        _canonical_token: Optional[str],
    ) -> List[float]:
        import zoneinfo

        et_timezone = zoneinfo.ZoneInfo("America/New_York")
        datetime_module = sys.modules.get("src.monitor.chart_generator.datetime")
        if datetime_module is None:
            import datetime as _datetime_module

            datetime_module = _datetime_module
        today_et = datetime_module.datetime.now(et_timezone).date()
        current_year_suffix = str(today_et.year)[-2:]
        month_str = today_et.strftime("%b").upper()
        day_str = f"{today_et.day:02d}"
        today_market_date = f"{current_year_suffix}{month_str}{day_str}"
        parse_fn = getattr(
            sys.modules.get("src.monitor.chart_generator"),
            "parse_kalshi_market_key",
            parse_kalshi_market_key,
        )
        strikes, primary_found = await self.gatherer.gather_strikes_for_tokens(
            redis_client=redis_client,
            tokens=city_tokens,
            parse_fn=parse_fn,
            today_et=today_et,
            et_timezone=et_timezone,
            today_market_date=today_market_date,
        )
        if not strikes:
            raise RuntimeError(f"No Kalshi strikes available for {station_icao}")
        if not primary_found:
            raise RuntimeError(f"No primary Kalshi strike data available for {station_icao}")
        return sorted(strikes)
