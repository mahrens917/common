import datetime
import importlib.util
import pathlib
from types import ModuleType

import pytest

from common.redis_protocol.parsing.kalshi_helpers import (
    parse_day_month_year_format,
    parse_intraday_format,
    parse_year_month_day_format,
)
from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError


def _load_strike_parser_module() -> ModuleType:
    module_path = pathlib.Path("src/common/redis_protocol/probability_store/keys_helpers.py")
    spec = importlib.util.spec_from_file_location(
        "common.redis_protocol.probability_store.keys_helpers_file", module_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_probability_strike_parsers_handle_variants():
    parser_module = _load_strike_parser_module()
    assert parser_module.parse_numeric_strike("10.5") == 10.5
    assert parser_module.parse_greater_than_strike(">12") == 12.0
    assert parser_module.parse_less_than_strike("<8.25") == 8.25
    assert parser_module.parse_range_strike("5-10") == 5.0


@pytest.mark.parametrize(
    "parser_name, value",
    [
        ("parse_numeric_strike", "abc"),
        ("parse_greater_than_strike", ">abc"),
        ("parse_less_than_strike", "<abc"),
        ("parse_range_strike", "bad-range"),
    ],
)
def test_probability_strike_parsers_raise_on_invalid(parser_name, value):
    parser_module = _load_strike_parser_module()
    parser = getattr(parser_module, parser_name)
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
