from datetime import datetime

import pytest

from common.redis_protocol.kalshi_store.reader_helpers import close_time_parser


def test_parse_close_time_success(monkeypatch):
    monkeypatch.setattr(
        close_time_parser,
        "parse_expiry_datetime",
        lambda value: datetime(2025, 1, 1),
    )
    result = close_time_parser.CloseTimeParser.parse_close_time_from_field("2025-01-01T00:00Z")
    assert result == datetime(2025, 1, 1)


def test_parse_close_time_invalid(monkeypatch):
    def raising(value):
        raise ValueError("bad")

    monkeypatch.setattr(close_time_parser, "parse_expiry_datetime", raising)
    assert close_time_parser.CloseTimeParser.parse_close_time_from_field("bad") is None


def test_decode_close_time_string_variants():
    assert close_time_parser.CloseTimeParser.decode_close_time_string(b"abc") == "abc"
    assert close_time_parser.CloseTimeParser.decode_close_time_string("xyz") == "xyz"
    assert close_time_parser.CloseTimeParser.decode_close_time_string(None) == ""
