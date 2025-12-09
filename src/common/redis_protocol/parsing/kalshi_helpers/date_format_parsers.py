"""Parse different Kalshi date token formats via the canonical parser."""

from datetime import datetime

from src.common.redis_protocol.parsing.kalshi import (
    parse_day_month_year_format as _canonical_parse_day_month_year_format,
)
from src.common.redis_protocol.parsing.kalshi import (
    parse_intraday_format as _canonical_parse_intraday_format,
)
from src.common.redis_protocol.parsing.kalshi import (
    parse_year_month_day_format as _canonical_parse_year_month_day_format,
)


def parse_year_month_day_format(token: str, prefix: str, month: int, remainder: str) -> datetime:
    """Parse YYMMMDD format (e.g., 25JAN15) using the canonical implementation."""
    return _canonical_parse_year_month_day_format(token, prefix, month, remainder)


def parse_intraday_format(
    token: str, now: datetime, month: int, day: int, remainder: str
) -> datetime:
    """Parse DDMMMHHMM format (e.g., 15JAN1530) using the canonical implementation."""
    return _canonical_parse_intraday_format(token, now, month, day, remainder)


def parse_day_month_year_format(token: str, month: int, day: int, remainder: str) -> datetime:
    """Parse DDMMMYY format (e.g., 15JAN25) using the canonical implementation."""
    return _canonical_parse_day_month_year_format(token, month, day, remainder)
