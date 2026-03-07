import datetime

import pytest

from common.redis_protocol.parsing.kalshi import (
    parse_day_month_year_format,
    parse_intraday_format,
    parse_year_month_day_format,
)
from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError
from common.redis_protocol.probability_store.keys import (
    parse_greater_than_strike,
    parse_less_than_strike,
    parse_numeric_strike,
    parse_range_strike,
)


def test_probability_strike_parsers_handle_variants():
    assert parse_numeric_strike("10.5") == 10.5
    assert parse_greater_than_strike(">12") == 12.0
    assert parse_less_than_strike("<8.25") == 8.25
    assert parse_range_strike("5-10") == 5.0


@pytest.mark.parametrize(
    "parser, value",
    [
        (parse_numeric_strike, "abc"),
        (parse_greater_than_strike, ">abc"),
        (parse_less_than_strike, "<abc"),
        (parse_range_strike, "bad-range"),
    ],
)
def test_probability_strike_parsers_raise_on_invalid(parser, value):
    with pytest.raises(ProbabilityStoreError):
        parser(value)


def test_kalshi_helper_parsers_return_expected_dates():
    now = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    # YYMMMDD
    dt_full = parse_year_month_day_format("25JAN05", "25", 1, "05")
    assert dt_full.year == 2025 and dt_full.month == 1 and dt_full.day == 6

    # DDMMMYY
    dt_day_month_year = parse_day_month_year_format("05JAN25", 1, 5, "25")
    assert dt_day_month_year.year == 2025 and dt_day_month_year.hour == 8

    # DDMMMHHMM - before now uses same year
    dt_intraday = parse_intraday_format("05JAN1530", now, 1, 5, "1530")
    assert dt_intraday.year == 2025 and dt_intraday.hour == 15 and dt_intraday.minute == 30
