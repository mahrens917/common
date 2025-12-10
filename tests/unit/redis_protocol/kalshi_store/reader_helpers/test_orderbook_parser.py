import pytest

from common.exceptions import DataError
from common.redis_protocol.kalshi_store.reader_helpers import orderbook_parser


def test_extract_orderbook_sizes_valid():
    orderbook = {"orderbook": '{"yes_bids": {"1.0": 1}, "yes_asks": {"2.0": 2}}'}
    result = orderbook_parser.extract_orderbook_sizes("T", orderbook)
    assert isinstance(result, tuple)


def test_extract_orderbook_sizes_missing_orderbook():
    with pytest.raises(DataError):
        orderbook_parser.extract_orderbook_sizes("T", {})


def test_parse_orderbook_json_returns_dict(monkeypatch):
    parsed = orderbook_parser.parse_orderbook_json(b'{"key": "value"}', "field", "T")
    assert "key" in parsed


def test_resolve_orderbook_size_errors():
    with pytest.raises(RuntimeError):
        orderbook_parser.resolve_orderbook_size({}, 1.0, "T")
