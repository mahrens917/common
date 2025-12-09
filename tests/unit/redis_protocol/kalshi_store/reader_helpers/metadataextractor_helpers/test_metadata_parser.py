"""Tests for metadata parser."""

from src.common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.metadata_parser import (
    MetadataParser,
)


def test_parse_market_metadata_returns_none_when_missing():
    assert MetadataParser.parse_market_metadata("T", {}) is None


def test_parse_market_metadata_returns_dict_for_json():
    result = MetadataParser.parse_market_metadata("T", {"metadata": b'{"foo": 1}'})
    assert result == {"foo": 1}


def test_parse_market_metadata_logs_warning_on_invalid(caplog):
    metadata = {"metadata": b"{bad"}
    with caplog.at_level("WARNING"):
        assert MetadataParser.parse_market_metadata("T", metadata) is None
    assert "Invalid metadata JSON" in caplog.text
