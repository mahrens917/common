from __future__ import annotations

from datetime import datetime, timezone

import pytest

from common.exceptions import DataError, ValidationError
from common.redis_protocol.parsing.kalshi import (
    derive_strike_fields,
    parse_expiry_token,
)


def test_parse_expiry_token_intraday_and_year_formats():
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    intraday = parse_expiry_token("01JAN1530", now=now)
    assert intraday.year == now.year
    assert intraday.hour == 15
    assert intraday.minute == 30

    yyyy = parse_expiry_token("25JAN01", now=now)
    assert yyyy.year == 2025
    assert yyyy.month == 1


def test_parse_expiry_token_validation_errors():
    with pytest.raises(ValueError):
        parse_expiry_token("01JAN", now=datetime.now(timezone.utc))

    with pytest.raises(DataError):
        parse_expiry_token("01JANABCD", now=datetime.now(timezone.utc))

    assert parse_expiry_token("bad") is None


def test_derive_strike_fields_handles_variants():
    assert derive_strike_fields("") is None
    assert derive_strike_fields("BTC-X") is None

    strike_type, floor_strike, cap_strike, strike_value = derive_strike_fields("BTC-T50")
    assert strike_type == "greater"
    assert floor_strike == 50
    assert cap_strike is None
    assert strike_value == 50

    strike_type, floor_strike, cap_strike, strike_value = derive_strike_fields("BTC-B10")
    assert strike_type == "less"
    assert floor_strike is None
    assert cap_strike == 10
    assert strike_value == 10

    strike_type, floor_strike, cap_strike, strike_value = derive_strike_fields("BTC-M99")
    assert strike_type == "between"
    assert floor_strike is None
    assert cap_strike is None
    assert strike_value == 99
