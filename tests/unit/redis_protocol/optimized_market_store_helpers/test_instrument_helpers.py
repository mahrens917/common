from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import List

import pytest
import redis.exceptions

from common.redis_protocol.optimized_market_store_helpers.instrument_fetcher import (
    InstrumentFetcher,
)
from common.redis_protocol.optimized_market_store_helpers.instrument_name_builder import (
    InstrumentNameBuilder,
)
from common.redis_schema import DeribitInstrumentDescriptor, DeribitInstrumentType


@pytest.mark.asyncio
async def test_instrument_fetcher_filters_instruments_by_type(monkeypatch):
    fetcher = InstrumentFetcher(lambda: None)

    captured_currency: List[str] = []

    class FakeScanner:
        def __init__(self):
            self.calls: list[str] = []

        async def scan_and_fetch_instruments(self, currency: str):
            captured_currency.append(currency)
            return ["raw"]

    class FakeBuilder:
        def __init__(self):
            self.calls: list[list] = []

        @staticmethod
        def build_instruments(scan_results):
            return [
                SimpleNamespace(is_future=False, option_type="put"),
                SimpleNamespace(is_future=True, option_type=None),
            ]

    fetcher._scanner = FakeScanner()
    fetcher._builder = FakeBuilder()

    assert await fetcher.get_all_instruments("btc")
    assert captured_currency == ["btc"]
    assert [i.is_future for i in await fetcher.get_futures_by_currency("btc")] == [True]
    assert [i.option_type for i in await fetcher.get_puts_by_currency("btc")] == ["put"]
    assert await fetcher.get_options_by_currency("btc")  # exercises non-future filter


@pytest.mark.asyncio
async def test_instrument_fetcher_handles_redis_errors(monkeypatch):
    fetcher = InstrumentFetcher(lambda: None)

    async def _raise(_currency):
        raise redis.exceptions.RedisError("boom")

    monkeypatch.setattr(fetcher, "get_all_instruments", _raise)

    assert await fetcher.get_options_by_currency("eth") == []
    assert await fetcher.get_futures_by_currency("eth") == []
    assert await fetcher.get_puts_by_currency("eth") == []


def _descriptor(**overrides) -> DeribitInstrumentDescriptor:
    base = DeribitInstrumentDescriptor(
        key="k",
        instrument_type=DeribitInstrumentType.OPTION,
        currency="btc",
        expiry_iso="2024-08-25",
        expiry_token="25AUG24",
        strike="25000",
        option_kind="c",
        quote_currency="usd",
    )
    return replace(base, **overrides)


def test_instrument_name_builder_handles_spot_and_future():
    spot_descriptor = _descriptor(instrument_type=DeribitInstrumentType.SPOT, quote_currency="")
    assert InstrumentNameBuilder.derive_instrument_name(spot_descriptor, strike_value=None, option_type=None) == "BTC-USD"

    future_descriptor = _descriptor(instrument_type=DeribitInstrumentType.FUTURE)
    assert InstrumentNameBuilder.derive_instrument_name(future_descriptor, strike_value=None, option_type=None) == "BTC-25AUG24"


def test_instrument_name_builder_formats_options_and_strikes():
    call_descriptor = _descriptor(option_kind="call", strike="20000", expiry_iso="2024-01-01", expiry_token=None)
    assert InstrumentNameBuilder.derive_instrument_name(call_descriptor, strike_value=20000, option_type=None) == "BTC-01JAN24-20000-C"

    put_descriptor = _descriptor(option_kind=None, strike="123.456", expiry_token=None)
    assert InstrumentNameBuilder.derive_instrument_name(put_descriptor, strike_value=123.456, option_type="put").endswith("-123.456-P")


def test_instrument_name_builder_handles_expiry_formats_and_missing_currency():
    descriptor = _descriptor(expiry_iso="2024-12-31", expiry_token=None)
    assert InstrumentNameBuilder._resolve_expiry_token(descriptor) == "31DEC24"

    descriptor_no_date = _descriptor(expiry_iso=None, expiry_token="bad-date")
    assert InstrumentNameBuilder._resolve_expiry_token(descriptor_no_date) == "BAD-DATE"

    with pytest.raises(ValueError):
        InstrumentNameBuilder.derive_instrument_name(_descriptor(currency=""), strike_value=None, option_type=None)
