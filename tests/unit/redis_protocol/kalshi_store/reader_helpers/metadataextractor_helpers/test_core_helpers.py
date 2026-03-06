import orjson

from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.type_converter import (
    normalize_hash,
    normalize_timestamp,
    string_or_default,
)
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.utilities import (
    extract_market_prices,
    parse_market_metadata,
    sync_top_of_book_fields,
)
from common.strike_helpers import calculate_strike_value, parse_strike_bounds


def test_price_extractor_parses_numbers_and_handles_missing():
    metadata = {"yes_bid": "1.5", "yes_ask": None}
    assert extract_market_prices(metadata) == (1.5, None)

    metadata = {"yes_bid": "", "yes_ask": "invalid"}
    assert extract_market_prices(metadata) == (None, None)


def test_timestamp_normalizer_delegates(monkeypatch):
    """Verify timestamp_normalizer delegates to canonical normalize_timestamp."""
    import common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization as tn

    sentinel = object()
    monkeypatch.setattr(tn, "normalize_timestamp", lambda value: sentinel)
    assert normalize_timestamp("ignored") is sentinel

    monkeypatch.setattr(tn, "normalize_timestamp", lambda value: None)
    assert normalize_timestamp("ignored") is None


def test_orderbook_syncer_calls_shared_helper(monkeypatch):
    captured = {}

    def fake_sync(snapshot):
        captured["snapshot"] = snapshot

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.utilities._sync_top_of_book_fields",
        fake_sync,
    )

    snapshot = {"yes_bid": 1.0}
    sync_top_of_book_fields(snapshot)
    assert captured["snapshot"] is snapshot


def test_metadata_parser_returns_metadata_and_handles_errors(caplog):
    payload = orjson.dumps({"foo": "bar"})
    assert parse_market_metadata("XYZ", {"metadata": payload}) == {"foo": "bar"}

    with caplog.at_level("WARNING"):
        result = parse_market_metadata("XYZ", {"metadata": "bad json"})
        assert result is None
        assert "Invalid metadata JSON for market XYZ" in caplog.text

    assert parse_market_metadata("XYZ", {}) is None


def test_strike_helpers_handle_types():
    floor_val, cap_val = parse_strike_bounds("10", "14")
    assert calculate_strike_value("between", floor_val, cap_val) == 12.0

    floor_val, cap_val = parse_strike_bounds("5", None)
    assert calculate_strike_value("greater", floor_val, cap_val) == 5.0

    floor_val, cap_val = parse_strike_bounds(None, "8")
    assert calculate_strike_value("less", floor_val, cap_val) == 8.0

    floor_val, cap_val = parse_strike_bounds(None, "9")
    assert calculate_strike_value("less", floor_val, cap_val) == 9.0


def test_type_converter_handles_strings_and_bytes():
    assert string_or_default(None, fill_value="X") == "X"
    assert string_or_default(123) == "123"
    normalized = normalize_hash({b"key": b"value", "int": 3})
    assert normalized == {"key": "value", "int": 3}
