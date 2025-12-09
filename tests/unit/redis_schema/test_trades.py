from datetime import date

import pytest

from src.common.redis_schema.trades import (
    TradeIndexKey,
    TradeRecordKey,
    TradeSummaryKey,
)


def test_trade_record_key_sanitizes_segments():
    key = TradeRecordKey(date(2024, 5, 17), "Order 123").key()
    assert key == "trades:record:2024-05-17:order_123"


def test_trade_record_key_rejects_invalid_characters():
    with pytest.raises(ValueError):
        TradeRecordKey(date(2024, 5, 17), "invalid/id").key()


def test_trade_index_key_sanitizes_type_and_value():
    key = TradeIndexKey("Station-Name", "Alpha Beta").key()
    assert key == "trades:index:station-name:alpha_beta"


def test_trade_summary_key_serialises_date():
    key = TradeSummaryKey(date(2023, 12, 31)).key()
    assert key == "trades:summary:2023-12-31"
