from types import SimpleNamespace

from common.redis_protocol.kalshi_store.reader_helpers import metadata_extractor


def _monkeypatch_helpers(monkeypatch):
    monkeypatch.setattr(metadata_extractor, "string_or_default", lambda value, fill_value="": value or fill_value)
    monkeypatch.setattr(metadata_extractor, "normalize_hash", lambda raw_hash: {"normalized": True})
    monkeypatch.setattr(metadata_extractor, "sync_top_of_book_fields", lambda snapshot: snapshot.__setitem__("synced", True))
    monkeypatch.setattr(
        metadata_extractor,
        "parse_market_metadata",
        lambda ticker, data: {"close_time": data.get("close_time"), "strike": 1.0},
    )
    monkeypatch.setattr(metadata_extractor, "resolve_market_strike", lambda meta, converter: 2.0)
    monkeypatch.setattr(metadata_extractor, "extract_market_prices", lambda meta: (1.0, 2.0))
    monkeypatch.setattr(metadata_extractor, "normalize_timestamp", lambda value: "2025-01-01")

    class DummyMarketRecordBuilder:
        def __init__(self, converter, timestamp, strike_resolver):
            pass

        def create_market_record(self, market_ticker, raw_hash, **kwargs):
            return {"ticker": market_ticker, "normalized": True}

    monkeypatch.setattr(metadata_extractor, "MarketRecordBuilder", DummyMarketRecordBuilder)


def test_metadata_extractor_static_helpers(monkeypatch):
    _monkeypatch_helpers(monkeypatch)
    extractor = metadata_extractor.MetadataExtractor(logger_instance=SimpleNamespace())
    assert extractor.string_or_default("", fill_value="X") == "X"
    assert extractor.normalize_hash({}) == {"normalized": True}
    snapshot = {}
    extractor.sync_top_of_book_fields(snapshot)
    assert snapshot["synced"] is True
    assert extractor.parse_market_metadata("T", {"close_time": "now"})["close_time"] == "now"
    assert extractor.resolve_market_strike({"strike": 1.0}) == 2.0
    assert extractor.extract_market_prices({}) == (1.0, 2.0)
    assert extractor.normalize_timestamp(None) == "2025-01-01"
    record = extractor.create_market_record("TK", {}, currency="BTC", now="now")
    assert record["ticker"] == "TK"
