import pytest

from common.exceptions import DataError
from common.redis_protocol.kalshi_store.reader_helpers import market_aggregator


def test_aggregate_markets_by_point_success():
    aggregator = market_aggregator.MarketAggregator()
    markets = [
        {"expiry": "2025-01-01", "strike": 1.0, "strike_type": "call", "market_ticker": "TK1"},
        {"expiry": "2025-01-01", "strike": 1.0, "strike_type": "call", "market_ticker": "TK2"},
    ]
    grouped, by_ticker = aggregator.aggregate_markets_by_point(markets)
    assert len(grouped) == 1
    assert "TK1" in by_ticker


def test_aggregate_raises_on_missing_fields():
    aggregator = market_aggregator.MarketAggregator()
    with pytest.raises(DataError):
        aggregator.aggregate_markets_by_point([{"expiry": None, "strike": 1.0, "strike_type": "call", "market_ticker": "TK1"}])


def test_aggregate_raises_on_non_numeric_strike():
    aggregator = market_aggregator.MarketAggregator()
    with pytest.raises(RuntimeError):
        aggregator.aggregate_markets_by_point(
            [
                {
                    "expiry": "2025-01-01",
                    "strike": "not-a-number",
                    "strike_type": "call",
                    "market_ticker": "TK1",
                }
            ]
        )
