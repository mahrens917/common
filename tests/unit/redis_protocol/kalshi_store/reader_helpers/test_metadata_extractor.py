from types import SimpleNamespace

from common.redis_protocol.kalshi_store.reader_helpers import metadata_extractor


def _monkeypatch_helpers(monkeypatch):
    class DummyConverter:
        @staticmethod
        def string_or_default(value, default=""):
            return value or default

        @staticmethod
        def normalize_hash(raw_hash):
            return {"normalized": True}

    class DummyOrderbookSyncer:
        @staticmethod
        def sync_top_of_book_fields(snapshot):
            snapshot["synced"] = True

    class DummyParser:
        @staticmethod
        def parse_market_metadata(ticker, data):
            return {"close_time": data.get("close_time"), "strike": 1.0}

    class DummyResolver:
        @staticmethod
        def resolve_market_strike(meta, fallback):
            return 2.0

    class DummyPriceExtractor:
        @staticmethod
        def extract_market_prices(meta):
            return 1.0, 2.0

    class DummyTimestampNormalizer:
        @staticmethod
        def normalize_timestamp(value):
            return "2025-01-01"

    class DummyMarketRecordBuilder:
        def __init__(self, converter, timestamp, strike_resolver):
            pass

        def create_market_record(self, market_ticker, raw_hash, **kwargs):
            return {"ticker": market_ticker, "normalized": True}

    monkeypatch.setattr(metadata_extractor, "TypeConverter", DummyConverter)
    monkeypatch.setattr(metadata_extractor, "OrderbookSyncer", DummyOrderbookSyncer)
    monkeypatch.setattr(metadata_extractor, "MetadataParser", DummyParser)
    monkeypatch.setattr(metadata_extractor, "StrikeResolver", DummyResolver)
    monkeypatch.setattr(metadata_extractor, "PriceExtractor", DummyPriceExtractor)
    monkeypatch.setattr(metadata_extractor, "TimestampNormalizer", DummyTimestampNormalizer)
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
