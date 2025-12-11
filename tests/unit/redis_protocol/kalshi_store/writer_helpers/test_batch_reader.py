from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.kalshi_store.writer_helpers.batch_reader import BatchReader


def make_default_funcs():
    return (
        str,
        lambda v, d=0: int(v) if v is not None else d,
        lambda v, d=0.0: float(v) if v is not None else d,
    )


@pytest.mark.asyncio
async def test_get_interpolation_results_returns_empty_when_no_keys(caplog):
    reader = BatchReader(redis_connection=MagicMock(), logger_instance=MagicMock())
    result = await reader.get_interpolation_results("USD", [], *make_default_funcs())
    assert result == {}


@pytest.mark.asyncio
async def test_get_interpolation_results_skips_invalid_entries():
    redis = MagicMock()
    # First key valid, second missing data
    redis.hgetall = AsyncMock(
        side_effect=[
            {
                "t_yes_bid": "1.0",
                "t_yes_ask": "2.0",
                "deribit_points_used": "1",
                "interp_error_bid": "0",
            },
            {},
        ]
    )
    reader = BatchReader(redis_connection=redis, logger_instance=MagicMock())

    class Desc:
        def __init__(self, ticker):
            self.ticker = ticker

    fake_module = SimpleNamespace(parse_kalshi_market_key=MagicMock(side_effect=[Desc("USD-TEST"), Desc("USD-FAIL")]))
    with patch.dict("sys.modules", {"common.redis_protocol.kalshi_store": fake_module}):
        result = await reader.get_interpolation_results("USD", ["k1", "k2"], *make_default_funcs())

    assert "USD-TEST" in result
    assert "t_yes_bid" in result["USD-TEST"]
    assert "USD-FAIL" not in result


@pytest.mark.asyncio
async def test_extract_single_interpolation_result_validates_currency():
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value={"t_yes_bid": "1.0", "t_yes_ask": "2.0"})
    reader = BatchReader(redis_connection=redis, logger_instance=MagicMock())

    class Desc:
        ticker = "EUR-TEST"

    res = await reader._extract_single_interpolation_result("k", "USD", lambda _k: Desc(), str, int, float)

    assert res is None


@pytest.mark.asyncio
async def test_extract_single_interpolation_result_handles_parse_errors(caplog):
    redis = MagicMock()
    reader = BatchReader(redis_connection=redis, logger_instance=MagicMock())

    def parser(_):
        raise ValueError("bad")

    res = await reader._extract_single_interpolation_result("k", "USD", parser, str, int, float)
    assert res is None
