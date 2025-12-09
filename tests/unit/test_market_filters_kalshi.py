from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Tuple

import pytest

from src.common.market_filters import kalshi

_TEST_COUNT_3 = 3
_TEST_COUNT_4 = 4
_VAL_0_42 = 0.42
_VAL_0_58 = 0.58
_VAL_15_0 = 15.0


def test_decode_handles_bytes_and_strings() -> None:
    assert kalshi.decode_payload("text") == "text"
    assert kalshi.decode_payload(b"bytes") == "bytes"
    assert kalshi.decode_payload(None) is None


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("None", None),
        ("12.5", 12.5),
        (b"3.14", 3.14),
        ("nan", None),
        ("inf", None),
        ("invalid", None),
        (object(), None),
    ],
)
def test_to_float(value: Any, expected: Optional[float]) -> None:
    assert kalshi.to_float_value(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("None", None),
        ("10", 10),
        ("10.7", 10),
        (b"5", 5),
        ("bad", None),
        (object(), None),
    ],
)
def test_to_int(value: Any, expected: Optional[int]) -> None:
    assert kalshi.to_int_value(value) == expected


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"1": "2"}, {"1": "2"}),
        ('{"1": "2"}', {"1": "2"}),
        (b'{"1": "2"}', {"1": "2"}),
        ("", {}),
        (b"", {}),
        ("invalid", {}),
        ([], {}),
    ],
)
def test_normalise_orderbook(payload: Any, expected: Mapping[str, Any]) -> None:
    assert kalshi._normalise_orderbook(payload) == expected


def test_extract_best_bid_and_ask_selects_extremes() -> None:
    payload = {"0.49": "10", "0.50": "5", "bad": "value", "0.30": "-1"}
    assert kalshi.extract_best_bid(payload) == (0.5, 5)
    assert kalshi.extract_best_ask(payload) == (0.49, 10)


def test_parse_expiry_datetime_handles_z_suffix() -> None:
    expiry = kalshi.parse_expiry_datetime("2024-05-01T12:30:00Z")
    assert expiry == datetime(2024, 5, 1, 12, 30, tzinfo=timezone.utc)


def test_parse_expiry_datetime_raises_for_invalid_input() -> None:
    with pytest.raises(ValueError):
        kalshi.parse_expiry_datetime("")

    with pytest.raises(ValueError):
        kalshi.parse_expiry_datetime("not-a-date")


def test_resolve_top_of_book_prefers_orderbook_and_falls_back() -> None:
    metadata = {"yes_bid": "0.3", "yes_bid_size": "4", "yes_ask": "0.7", "yes_ask_size": "6"}
    orderbook = {"yes_bids": {"0.35": "3"}, "yes_asks": {"0.65": "2"}}

    (bid_price, bid_size), (ask_price, ask_size), has_orderbook = kalshi._resolve_top_of_book(
        metadata, orderbook
    )

    assert (bid_price, bid_size) == (0.35, 3)
    assert (ask_price, ask_size) == (0.65, 2)
    assert has_orderbook is True


def test_resolve_top_of_book_uses_metadata_when_orderbook_missing() -> None:
    metadata = {"yes_bid": "0.4", "yes_bid_size": "9", "yes_ask": "0.6", "yes_ask_size": "7"}

    (bid_price, bid_size), (ask_price, ask_size), has_orderbook = kalshi._resolve_top_of_book(
        metadata, None
    )

    assert (bid_price, bid_size) == (0.4, 9)
    assert (ask_price, ask_size) == (0.6, 7)
    assert has_orderbook is False


def _base_metadata() -> dict[str, Any]:
    return {
        "close_time": "2099-01-01T00:00:00Z",
        "ticker": "KXBTC-TEST",
        "strike_type": "greater",
        "floor_strike": "1",
        "yes_bid": "0.2",
        "yes_bid_size": "10",
        "yes_ask": "0.8",
        "yes_ask_size": "5",
    }


def test_validate_kalshi_market_handles_empty_metadata() -> None:
    result = kalshi.validate_kalshi_market({})
    assert result.is_valid is False
    assert result.reason == "empty_data"


def test_validate_kalshi_market_rejects_missing_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = _base_metadata()
    metadata.pop("close_time")

    result = kalshi.validate_kalshi_market(metadata)
    assert result.is_valid is False
    assert result.reason == "missing_close_time"


def test_validate_kalshi_market_rejects_unparseable_expiry() -> None:
    metadata = _base_metadata()
    metadata["close_time"] = "bad-date"

    result = kalshi.validate_kalshi_market(metadata)

    assert result.is_valid is False
    assert result.reason == "unparseable_expiry"


def test_validate_kalshi_market_rejects_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = _base_metadata()
    metadata["close_time"] = "2020-01-01T00:00:00Z"

    now = datetime(2021, 1, 1, tzinfo=timezone.utc)
    result = kalshi.validate_kalshi_market(metadata, now=now)

    assert result.is_valid is False
    assert result.reason == "expired"


def test_validate_kalshi_market_rejects_unsupported_ticker(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = _base_metadata()
    monkeypatch.setattr(kalshi, "is_supported_kalshi_ticker", lambda ticker: False, raising=False)

    result = kalshi.validate_kalshi_market(metadata)
    assert result.is_valid is False
    assert result.reason == "unsupported_category"


def test_validate_kalshi_market_rejects_unknown_strike_type() -> None:
    metadata = _base_metadata()
    metadata["strike_type"] = None

    result = kalshi.validate_kalshi_market(metadata)
    assert result.is_valid is False
    assert result.reason == "unknown_strike_type"


@pytest.mark.parametrize(
    "strike_type,extras,expected_reason",
    [
        ("between", {"floor_strike": None}, "between_missing_bounds"),
        ("between", {"cap_strike": None}, "between_missing_bounds"),
        ("greater", {"floor_strike": None}, "greater_missing_floor"),
        ("less", {"cap_strike": None}, "less_missing_cap"),
    ],
)
def test_validate_kalshi_market_rejects_missing_strike_bounds(
    strike_type: str, extras: dict[str, Optional[str]], expected_reason: str
) -> None:
    metadata = _base_metadata()
    metadata["strike_type"] = strike_type
    metadata.update(extras)

    result = kalshi.validate_kalshi_market(metadata)
    assert result.is_valid is False
    assert result.reason == expected_reason


def test_validate_kalshi_market_allows_missing_pricing_when_disabled() -> None:
    metadata = _base_metadata()
    metadata.pop("yes_bid")
    metadata.pop("yes_ask")

    result = kalshi.validate_kalshi_market(metadata, require_pricing=False)
    assert result.is_valid is True
    assert result.yes_bid_price is None
    assert result.yes_ask_price is None


def test_validate_kalshi_market_requires_pricing_when_enabled() -> None:
    metadata = _base_metadata()
    metadata.pop("yes_bid")
    metadata.pop("yes_ask")

    result = kalshi.validate_kalshi_market(metadata, require_pricing=True)

    assert result.is_valid is False
    assert result.reason == "missing_pricing_data"


def test_validate_kalshi_market_between_strike_computation(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = _base_metadata()
    metadata["strike_type"] = "between"
    metadata["floor_strike"] = "10"
    metadata["cap_strike"] = "20"
    monkeypatch.setattr(kalshi, "is_supported_kalshi_ticker", lambda ticker: True, raising=False)

    now = datetime(2090, 1, 1, tzinfo=timezone.utc)
    result = kalshi.validate_kalshi_market(metadata, now=now)

    assert result.is_valid is True
    assert result.strike == _VAL_15_0
    assert result.strike_type == "between"


def test_validate_kalshi_market_success_with_orderbook(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = _base_metadata()
    orderbook = {"yes_bids": {"0.42": "4"}, "yes_asks": {"0.58": "3"}}
    monkeypatch.setattr(kalshi, "is_supported_kalshi_ticker", lambda ticker: True, raising=False)

    now = datetime(2090, 1, 1, tzinfo=timezone.utc)
    result = kalshi.validate_kalshi_market(metadata, now=now, orderbook=orderbook)

    assert result.is_valid is True
    assert result.yes_bid_price == _VAL_0_42
    assert result.yes_bid_size == _TEST_COUNT_4
    assert result.yes_ask_price == _VAL_0_58
    assert result.yes_ask_size == _TEST_COUNT_3
    assert result.has_orderbook is True
