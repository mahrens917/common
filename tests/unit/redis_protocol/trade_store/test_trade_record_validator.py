from unittest.mock import patch

from common.redis_protocol.trade_store.trade_record_validator import TradeRecordValidator


class TestTradeRecordValidator:
    def test_validate_required_fields(self):
        with patch(
            "common.redis_protocol.trade_store.codec_helpers.validators.validate_required_fields"
        ) as mock_val:
            data = {"test": 1}
            TradeRecordValidator.validate_required_fields(data)
            mock_val.assert_called_once_with(data)

    def test_validate_trade_metadata(self):
        with patch(
            "common.redis_protocol.trade_store.codec_helpers.validators.validate_trade_metadata"
        ) as mock_val:
            data = {"test": 1}
            TradeRecordValidator.validate_trade_metadata(data)
            mock_val.assert_called_once_with(data)

    def test_validate_weather_fields(self):
        with patch(
            "common.redis_protocol.trade_store.codec_helpers.validators.validate_weather_fields"
        ) as mock_val:
            data = {"test": 1}
            TradeRecordValidator.validate_weather_fields(data)
            mock_val.assert_called_once_with(data)
