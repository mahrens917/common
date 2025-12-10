from unittest.mock import Mock

import pytest

from common.redis_protocol.kalshi_store.writer_helpers.orderbook_writer_helpers.trade_mapping_builder import (
    build_trade_tick_mapping,
)


class TestTradeMappingBuilder:
    @pytest.fixture
    def mock_normalizer(self):
        normalizer = Mock()
        normalizer.normalise_trade_timestamp.return_value = "2023-01-01T12:00:00Z"
        return normalizer

    def test_build_trade_tick_mapping_full(self, mock_normalizer):
        """Test mapping with all fields present."""
        msg = {
            "ts": 1234567890,
            "count": 10,
            "taker_side": "yes",
        }
        side = "yes"
        yes_price = 50
        no_price = 50
        raw_price = 50

        mapping = build_trade_tick_mapping(
            msg, side, yes_price, no_price, raw_price, mock_normalizer
        )

        assert mapping["last_trade_side"] == "yes"
        assert mapping["last_trade_count"] == "10"
        assert mapping["last_trade_timestamp"] == "2023-01-01T12:00:00Z"
        assert mapping["last_trade_taker_side"] == "yes"
        assert mapping["last_trade_raw_price"] == "50"
        assert mapping["last_trade_yes_price"] == "50"
        assert mapping["last_price"] == "50"
        assert mapping["last_trade_no_price"] == "50"

    def test_build_trade_tick_mapping_alternatives(self, mock_normalizer):
        """Test mapping with alternative field names."""
        msg = {
            "timestamp": 1234567890,
            "quantity": 5,
            "taker": "no",
        }
        side = "no"

        mapping = build_trade_tick_mapping(msg, side, None, None, None, mock_normalizer)

        assert mapping["last_trade_side"] == "no"
        assert mapping["last_trade_count"] == "5"
        assert mapping["last_trade_taker_side"] == "no"
        assert "last_trade_yes_price" not in mapping

    def test_build_trade_tick_mapping_minimal(self, mock_normalizer):
        """Test mapping with missing optional fields."""
        msg = {}
        # Should handle missing fields gracefully
        mock_normalizer.normalise_trade_timestamp.return_value = ""

        mapping = build_trade_tick_mapping(msg, None, None, None, None, mock_normalizer)

        assert mapping["last_trade_side"] == ""
        assert mapping["last_trade_count"] == ""
        assert mapping["last_trade_timestamp"] == ""
        assert "last_trade_taker_side" not in mapping
        assert "last_trade_yes_price" not in mapping

    def test_build_trade_tick_mapping_size_fallback(self, mock_normalizer):
        """Test size fallback."""
        msg = {"size": 100}
        mapping = build_trade_tick_mapping(msg, "", None, None, None, mock_normalizer)
        assert mapping["last_trade_count"] == "100"
