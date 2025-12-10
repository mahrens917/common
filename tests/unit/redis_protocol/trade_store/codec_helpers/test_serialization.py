from datetime import datetime, timezone

import orjson
import pytest

from common.data_models.trade_record import TradeRecord, TradeSide
from common.redis_protocol.trade_store.codec_helpers.decoder import (
    decode_trade_record,
    ensure_mapping,
)
from common.redis_protocol.trade_store.codec_helpers.encoder import (
    encode_trade_record,
    trade_record_to_payload,
)


class TestTradeRecordSerialization:
    def test_trade_record_roundtrip(self):
        trade = TradeRecord(
            order_id="123",
            market_ticker="TEST-MARKET",
            trade_timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            trade_side=TradeSide.YES,
            quantity=10,
            price_cents=50,
            fee_cents=1,
            cost_cents=501,
            market_category="weather",
            trade_rule="rule1",
            trade_reason="reason1_longer_than_10",
            weather_station="KSFO",
            settlement_price_cents=100,
            settlement_time=datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            last_yes_bid=49,
            last_yes_ask=51,
            last_price_update=datetime(2023, 1, 1, 11, 59, 0, tzinfo=timezone.utc),
        )

        encoded = encode_trade_record(trade)
        decoded = decode_trade_record(encoded)

        assert decoded == trade

    def test_ensure_mapping_dict(self):
        data = {"a": 1}
        assert ensure_mapping(data) == data

    def test_ensure_mapping_bytes(self):
        data = b'{"a": 1}'
        assert ensure_mapping(data) == {"a": 1}

    def test_ensure_mapping_str(self):
        data = '{"a": 1}'
        assert ensure_mapping(data) == {"a": 1}

    def test_ensure_mapping_invalid_json(self):
        with pytest.raises(ValueError, match="Trade payload is not valid JSON"):
            ensure_mapping("{invalid")

    def test_ensure_mapping_invalid_type(self):
        with pytest.raises(TypeError, match="Unsupported payload type"):
            ensure_mapping(123)

    def test_trade_record_to_payload_optional_fields(self):
        trade = TradeRecord(
            order_id="123",
            market_ticker="TEST",
            trade_timestamp=datetime.now(timezone.utc),
            trade_side=TradeSide.NO,
            quantity=1,
            price_cents=10,
            fee_cents=0,
            cost_cents=10,
            market_category="macro",
            trade_rule="rule",
            trade_reason="reason_longer_than_10",
        )

        payload = trade_record_to_payload(trade)
        assert "weather_station" not in payload
        assert "settlement_price_cents" not in payload
