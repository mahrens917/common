"""Unit tests for common redis_protocol messages module."""

import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import orjson
import pytest

from src.common.exceptions import DataError, ValidationError
from src.common.redis_protocol.messages import (
    IndexMetadata,
    InstrumentMetadata,
    MarketData,
    PDFData,
    PriceIndexData,
    SubscriptionUpdate,
    VolatilityIndexData,
)


class TestMarketData:
    """Tests for MarketData dataclass."""

    def test_to_redis_hash_option(self):
        """Test converting option market data to Redis hash."""
        data = MarketData(
            instrument="BTC-31JAN25-60000-C",
            currency="BTC",
            strike_price=60000.0,
            expiry_timestamp=1738368000,  # 2025-02-01 00:00:00 UTC
            best_bid=0.05,
            best_ask=0.06,
            best_bid_size=100.0,
            best_ask_size=200.0,
            instrument_type="option",
            option_type="call",
            timestamp=1700000000,
        )

        result = data.to_redis_hash()

        assert result["best_bid"] == "0.05"
        assert result["best_ask"] == "0.06"
        assert result["best_bid_size"] == "100.0"
        assert result["best_ask_size"] == "200.0"
        assert result["currency"] == "BTC"
        assert result["instrument_type"] == "Option"
        assert result["strike_price"] == "60000.0"
        assert result["option_type"] == "call"
        assert "last_update" in result
        assert "expiry_date" in result

    def test_to_redis_hash_future(self):
        """Test converting future market data to Redis hash."""
        data = MarketData(
            instrument="BTC-31JAN25",
            currency="BTC",
            strike_price=0.0,
            expiry_timestamp=1738368000,
            best_bid=65000.0,
            best_ask=65100.0,
            best_bid_size=10.0,
            best_ask_size=15.0,
            instrument_type="future",
            option_type=None,
            timestamp=1700000000,
        )

        result = data.to_redis_hash()

        assert result["best_bid"] == "65000.0"
        assert result["best_ask"] == "65100.0"
        assert result["instrument_type"] == "Future"
        assert "option_type" not in result
        assert result["strike_price"] == "0.0"

    def test_to_redis_hash_default_timestamp(self):
        """Test that default timestamp is set when not provided."""
        data = MarketData(
            instrument="BTC-31JAN25-60000-C",
            currency="BTC",
            strike_price=60000.0,
            expiry_timestamp=1738368000,
            best_bid=0.05,
            best_ask=0.06,
            best_bid_size=100.0,
            best_ask_size=200.0,
        )

        with patch("time.time", return_value=1700000000):
            result = data.to_redis_hash()
            assert "last_update" in result

    def test_to_redis_hash_invalid_expiry_timestamp(self):
        """Test that invalid expiry timestamp raises ValidationError."""
        data = MarketData(
            instrument="BTC-31JAN25-60000-C",
            currency="BTC",
            strike_price=60000.0,
            expiry_timestamp=999999999999999,  # Invalid timestamp
            best_bid=0.05,
            best_ask=0.06,
            best_bid_size=100.0,
            best_ask_size=200.0,
        )

        with pytest.raises(ValidationError, match="Invalid expiry_timestamp"):
            data.to_redis_hash()

    def test_to_redis_hash_normalizes_option_type(self):
        """Test that option type is normalized."""
        data = MarketData(
            instrument="BTC-31JAN25-60000-P",
            currency="BTC",
            strike_price=60000.0,
            expiry_timestamp=1738368000,
            best_bid=0.05,
            best_ask=0.06,
            best_bid_size=100.0,
            best_ask_size=200.0,
            instrument_type="option",
            option_type="P",  # Abbreviated
            timestamp=1700000000,
        )

        result = data.to_redis_hash()
        assert result["option_type"] == "put"

    def test_from_redis_hash_option(self):
        """Test creating MarketData from Redis hash for option."""
        hash_data = {
            "currency": "BTC",
            "expiry_date": "2025-02-01T00:00:00Z",
            "instrument_type": "Option",
            "strike_price": "60000.0",
            "best_bid": "0.05",
            "best_ask": "0.06",
            "best_bid_size": "100.0",
            "best_ask_size": "200.0",
            "option_type": "call",
            "last_update": "2023-11-15T06:13:20Z",
        }

        result = MarketData.from_redis_hash("BTC-31JAN25-60000-C", hash_data)

        assert result.instrument == "BTC-31JAN25-60000-C"
        assert result.currency == "BTC"
        assert result.strike_price == 60000.0
        assert result.best_bid == 0.05
        assert result.best_ask == 0.06
        assert result.best_bid_size == 100.0
        assert result.best_ask_size == 200.0
        assert result.instrument_type == "option"
        assert result.option_type == "call"
        assert result.timestamp > 0

    def test_from_redis_hash_future(self):
        """Test creating MarketData from Redis hash for future."""
        hash_data = {
            "currency": "ETH",
            "expiry_date": "2025-02-01T00:00:00Z",
            "instrument_type": "Future",
            "strike_price": "0.0",
            "best_bid": "3500.0",
            "best_ask": "3505.0",
            "best_bid_size": "50.0",
            "best_ask_size": "75.0",
            "last_update": "2023-11-15T06:13:20Z",
        }

        result = MarketData.from_redis_hash("ETH-31JAN25", hash_data)

        assert result.instrument == "ETH-31JAN25"
        assert result.currency == "ETH"
        assert result.instrument_type == "future"
        assert result.option_type is None

    def test_from_redis_hash_missing_required_field(self):
        """Test that missing required field raises RuntimeError."""
        hash_data = {
            "currency": "BTC",
            "expiry_date": "2025-02-01T00:00:00Z",
            # Missing instrument_type
            "strike_price": "60000.0",
            "best_bid": "0.05",
            "best_ask": "0.06",
            "best_bid_size": "100.0",
            "best_ask_size": "200.0",
            "last_update": "2023-11-15T06:13:20Z",
        }

        with pytest.raises(RuntimeError, match="Missing required instrument_type"):
            MarketData.from_redis_hash("BTC-31JAN25-60000-C", hash_data)

    def test_from_redis_hash_invalid_float_field(self):
        """Test that invalid float field raises RuntimeError."""
        hash_data = {
            "currency": "BTC",
            "expiry_date": "2025-02-01T00:00:00Z",
            "instrument_type": "Option",
            "strike_price": "invalid",  # Not a valid float
            "best_bid": "0.05",
            "best_ask": "0.06",
            "best_bid_size": "100.0",
            "best_ask_size": "200.0",
            "last_update": "2023-11-15T06:13:20Z",
        }

        with pytest.raises(RuntimeError, match="cannot convert to float"):
            MarketData.from_redis_hash("BTC-31JAN25-60000-C", hash_data)

    def test_from_redis_hash_invalid_timestamp(self):
        """Test that invalid timestamp format raises DataError."""
        hash_data = {
            "currency": "BTC",
            "expiry_date": "invalid-date",
            "instrument_type": "Option",
            "strike_price": "60000.0",
            "best_bid": "0.05",
            "best_ask": "0.06",
            "best_bid_size": "100.0",
            "best_ask_size": "200.0",
            "last_update": "2023-11-15T06:13:20Z",
        }

        with pytest.raises(DataError, match="FAIL-FAST: Invalid timestamp format"):
            MarketData.from_redis_hash("BTC-31JAN25-60000-C", hash_data)


class TestPriceIndexData:
    """Tests for PriceIndexData dataclass."""

    def test_to_redis_hash(self):
        """Test converting price index data to Redis hash."""
        data = PriceIndexData(
            index_name="btc_usd",
            price=65000.50,
            timestamp=1700000000000,  # milliseconds
        )

        result = data.to_redis_hash()

        assert result["value"] == "65000.5"
        assert "last_update" in result

    def test_to_redis_hash_default_timestamp(self):
        """Test that default timestamp is set when not provided."""
        data = PriceIndexData(
            index_name="btc_usd",
            price=65000.50,
        )

        with patch("time.time", return_value=1700000000):
            result = data.to_redis_hash()
            assert "last_update" in result

    def test_from_redis_hash_with_value_field(self):
        """Test creating PriceIndexData from Redis hash with 'value' field."""
        hash_data = {
            "value": "65000.50",
            "last_update": "2023-11-15T06:13:20Z",
        }

        result = PriceIndexData.from_redis_hash("btc_usd", hash_data)

        assert result.index_name == "btc_usd"
        assert result.price == 65000.50
        assert result.timestamp > 0

    def test_from_redis_hash_with_price_field(self):
        """Test creating PriceIndexData from Redis hash with 'price' field."""
        hash_data = {
            "price": "65000.50",
            "last_update": "2023-11-15T06:13:20Z",
        }

        result = PriceIndexData.from_redis_hash("btc_usd", hash_data)

        assert result.index_name == "btc_usd"
        assert result.price == 65000.50

    def test_from_redis_hash_missing_price_field(self):
        """Test that missing price field raises RuntimeError."""
        hash_data = {
            "last_update": "2023-11-15T06:13:20Z",
        }

        with pytest.raises(RuntimeError, match="Missing required price field"):
            PriceIndexData.from_redis_hash("btc_usd", hash_data)

    def test_from_redis_hash_invalid_price_value(self):
        """Test that invalid price value raises ValueError."""
        hash_data = {
            "value": "not-a-number",
            "last_update": "2023-11-15T06:13:20Z",
        }

        with pytest.raises(ValueError):
            PriceIndexData.from_redis_hash("btc_usd", hash_data)

    def test_from_redis_hash_timestamp_conversion(self):
        """Test that timestamp is correctly converted to milliseconds."""
        hash_data = {
            "value": "65000.50",
            "last_update": "2023-11-15T06:13:20Z",
        }

        result = PriceIndexData.from_redis_hash("btc_usd", hash_data)

        # Timestamp should be in milliseconds
        assert result.timestamp > 1000000000000


class TestVolatilityIndexData:
    """Tests for VolatilityIndexData dataclass."""

    def test_to_redis_hash(self):
        """Test converting volatility index data to Redis hash."""
        data = VolatilityIndexData(
            index_name="btc_usd",
            volatility=0.75,
            timestamp=1700000000000,  # milliseconds
        )

        result = data.to_redis_hash()

        assert result["volatility"] == "0.75"
        assert "last_update" in result

    def test_to_redis_hash_default_timestamp(self):
        """Test that default timestamp is set when not provided."""
        data = VolatilityIndexData(
            index_name="btc_usd",
            volatility=0.75,
        )

        with patch("time.time", return_value=1700000000):
            result = data.to_redis_hash()
            assert "last_update" in result

    def test_from_redis_hash(self):
        """Test creating VolatilityIndexData from Redis hash."""
        hash_data = {
            "volatility": "0.75",
            "last_update": "2023-11-15T06:13:20Z",
        }

        result = VolatilityIndexData.from_redis_hash("btc_usd", hash_data)

        assert result.index_name == "btc_usd"
        assert result.volatility == 0.75
        assert result.timestamp > 0

    def test_from_redis_hash_missing_volatility_field(self):
        """Test that missing volatility field raises RuntimeError."""
        hash_data = {
            "last_update": "2023-11-15T06:13:20Z",
        }

        with pytest.raises(RuntimeError, match="Missing required volatility"):
            VolatilityIndexData.from_redis_hash("btc_usd", hash_data)

    def test_from_redis_hash_invalid_volatility_value(self):
        """Test that invalid volatility value raises RuntimeError."""
        hash_data = {
            "volatility": "invalid",
            "last_update": "2023-11-15T06:13:20Z",
        }

        with pytest.raises(RuntimeError, match="cannot convert to float"):
            VolatilityIndexData.from_redis_hash("btc_usd", hash_data)

    def test_from_redis_hash_timestamp_conversion(self):
        """Test that timestamp is correctly converted to milliseconds."""
        hash_data = {
            "volatility": "0.75",
            "last_update": "2023-11-15T06:13:20Z",
        }

        result = VolatilityIndexData.from_redis_hash("btc_usd", hash_data)

        # Timestamp should be in milliseconds
        assert result.timestamp > 1000000000000


class TestInstrumentMetadata:
    """Tests for InstrumentMetadata dataclass."""

    def test_to_json_option(self):
        """Test converting option metadata to JSON."""
        metadata = InstrumentMetadata(
            type="option",
            channel="quote.BTC-31JAN25-60000-P",
            currency="BTC",
            expiry="31JAN25",
            strike=60000.0,
            option_type="put",
        )

        result = metadata.to_json()
        data = orjson.loads(result)

        assert data["type"] == "option"
        assert data["channel"] == "quote.BTC-31JAN25-60000-P"
        assert data["currency"] == "BTC"
        assert data["expiry"] == "31JAN25"
        assert data["strike"] == 60000.0
        assert data["option_type"] == "put"

    def test_to_json_future(self):
        """Test converting future metadata to JSON."""
        metadata = InstrumentMetadata(
            type="future",
            channel="quote.BTC-31JAN25",
            currency="BTC",
            expiry="31JAN25",
        )

        result = metadata.to_json()
        data = orjson.loads(result)

        assert data["type"] == "future"
        assert data["channel"] == "quote.BTC-31JAN25"
        assert "strike" not in data
        assert "option_type" not in data

    def test_from_json_option(self):
        """Test creating InstrumentMetadata from JSON for option."""
        json_data = orjson.dumps(
            {
                "type": "option",
                "channel": "quote.BTC-31JAN25-60000-C",
                "currency": "BTC",
                "expiry": "31JAN25",
                "strike": 60000.0,
                "option_type": "call",
            }
        ).decode()

        result = InstrumentMetadata.from_json(json_data)

        assert result.type == "option"
        assert result.channel == "quote.BTC-31JAN25-60000-C"
        assert result.currency == "BTC"
        assert result.expiry == "31JAN25"
        assert result.strike == 60000.0
        assert result.option_type == "call"

    def test_from_json_future(self):
        """Test creating InstrumentMetadata from JSON for future."""
        json_data = orjson.dumps(
            {
                "type": "future",
                "channel": "quote.BTC-31JAN25",
                "currency": "BTC",
                "expiry": "31JAN25",
            }
        ).decode()

        result = InstrumentMetadata.from_json(json_data)

        assert result.type == "future"
        assert result.channel == "quote.BTC-31JAN25"
        assert result.strike == 0.0
        assert result.option_type == ""

    def test_roundtrip_serialization(self):
        """Test that to_json and from_json are symmetric."""
        original = InstrumentMetadata(
            type="option",
            channel="quote.BTC-31JAN25-60000-P",
            currency="BTC",
            expiry="31JAN25",
            strike=60000.0,
            option_type="put",
        )

        json_str = original.to_json()
        restored = InstrumentMetadata.from_json(json_str)

        assert restored.type == original.type
        assert restored.channel == original.channel
        assert restored.currency == original.currency
        assert restored.expiry == original.expiry
        assert restored.strike == original.strike
        assert restored.option_type == original.option_type


class TestIndexMetadata:
    """Tests for IndexMetadata dataclass."""

    def test_to_json(self):
        """Test converting index metadata to JSON."""
        metadata = IndexMetadata(channel="deribit_price_index.btc_usd")

        result = metadata.to_json()
        data = orjson.loads(result)

        assert data["channel"] == "deribit_price_index.btc_usd"

    def test_from_json(self):
        """Test creating IndexMetadata from JSON."""
        json_data = orjson.dumps({"channel": "deribit_price_index.btc_usd"}).decode()

        result = IndexMetadata.from_json(json_data)

        assert result.channel == "deribit_price_index.btc_usd"

    def test_roundtrip_serialization(self):
        """Test that to_json and from_json are symmetric."""
        original = IndexMetadata(channel="deribit_price_index.btc_usd")

        json_str = original.to_json()
        restored = IndexMetadata.from_json(json_str)

        assert restored.channel == original.channel


class TestSubscriptionUpdate:
    """Tests for SubscriptionUpdate dataclass."""

    def test_to_json_with_instrument_metadata(self):
        """Test converting subscription update with instrument metadata to JSON."""
        metadata = InstrumentMetadata(
            type="option",
            channel="quote.BTC-31JAN25-60000-C",
            currency="BTC",
            expiry="31JAN25",
            strike=60000.0,
            option_type="call",
        )
        update = SubscriptionUpdate(
            name="BTC-31JAN25-60000-C",
            subscription_type="instrument",
            action="subscribe",
            metadata=metadata,
            timestamp=1700000000,
        )

        result = update.to_json()
        data = orjson.loads(result)

        assert data["name"] == "BTC-31JAN25-60000-C"
        assert data["subscription_type"] == "instrument"
        assert data["action"] == "subscribe"
        assert data["timestamp"] == 1700000000
        assert "metadata" in data
        assert data["metadata"]["type"] == "option"

    def test_to_json_with_index_metadata(self):
        """Test converting subscription update with index metadata to JSON."""
        metadata = IndexMetadata(channel="deribit_price_index.btc_usd")
        update = SubscriptionUpdate(
            name="btc_usd",
            subscription_type="price_index",
            action="subscribe",
            metadata=metadata,
            timestamp=1700000000,
        )

        result = update.to_json()
        data = orjson.loads(result)

        assert data["name"] == "btc_usd"
        assert data["subscription_type"] == "price_index"
        assert data["metadata"]["channel"] == "deribit_price_index.btc_usd"

    def test_to_json_without_metadata(self):
        """Test converting subscription update without metadata to JSON."""
        update = SubscriptionUpdate(
            name="BTC-31JAN25-60000-C",
            subscription_type="instrument",
            action="unsubscribe",
            metadata=None,
            timestamp=1700000000,
        )

        result = update.to_json()
        data = orjson.loads(result)

        assert data["name"] == "BTC-31JAN25-60000-C"
        assert data["metadata"] == {}

    def test_to_json_default_timestamp(self):
        """Test that default timestamp is set when not provided."""
        update = SubscriptionUpdate(
            name="BTC-31JAN25-60000-C",
            subscription_type="instrument",
            action="subscribe",
        )

        with patch("time.time", return_value=1700000000):
            result = update.to_json()
            data = orjson.loads(result)
            assert data["timestamp"] == 1700000000

    def test_from_json_with_instrument_metadata(self):
        """Test creating SubscriptionUpdate from JSON with instrument metadata."""
        json_data = orjson.dumps(
            {
                "name": "BTC-31JAN25-60000-C",
                "subscription_type": "instrument",
                "action": "subscribe",
                "metadata": {
                    "type": "option",
                    "channel": "quote.BTC-31JAN25-60000-C",
                    "currency": "BTC",
                    "expiry": "31JAN25",
                    "strike": 60000.0,
                    "option_type": "call",
                },
                "timestamp": 1700000000,
            }
        ).decode()

        result = SubscriptionUpdate.from_json(json_data)

        assert result.name == "BTC-31JAN25-60000-C"
        assert result.subscription_type == "instrument"
        assert result.action == "subscribe"
        assert result.timestamp == 1700000000
        assert isinstance(result.metadata, InstrumentMetadata)
        assert result.metadata.type == "option"

    def test_from_json_with_index_metadata(self):
        """Test creating SubscriptionUpdate from JSON with index metadata."""
        json_data = orjson.dumps(
            {
                "name": "btc_usd",
                "subscription_type": "price_index",
                "action": "subscribe",
                "metadata": {
                    "channel": "deribit_price_index.btc_usd",
                },
                "timestamp": 1700000000,
            }
        ).decode()

        result = SubscriptionUpdate.from_json(json_data)

        assert result.name == "btc_usd"
        assert result.subscription_type == "price_index"
        assert isinstance(result.metadata, IndexMetadata)
        assert result.metadata.channel == "deribit_price_index.btc_usd"

    def test_from_json_without_metadata(self):
        """Test creating SubscriptionUpdate from JSON without metadata."""
        json_data = orjson.dumps(
            {
                "name": "BTC-31JAN25-60000-C",
                "subscription_type": "instrument",
                "action": "unsubscribe",
                "timestamp": 1700000000,
            }
        ).decode()

        result = SubscriptionUpdate.from_json(json_data)

        assert result.name == "BTC-31JAN25-60000-C"
        assert result.metadata is None

    def test_from_json_filters_extra_index_metadata_fields(self):
        """Test that extra fields in index metadata are filtered out."""
        json_data = orjson.dumps(
            {
                "name": "btc_usd",
                "subscription_type": "volatility_index",
                "action": "subscribe",
                "metadata": {
                    "channel": "deribit_volatility_index.btc_usd",
                    "extra_field": "should_be_filtered",
                },
                "timestamp": 1700000000,
            }
        ).decode()

        result = SubscriptionUpdate.from_json(json_data)

        assert isinstance(result.metadata, IndexMetadata)
        assert result.metadata.channel == "deribit_volatility_index.btc_usd"
        assert not hasattr(result.metadata, "extra_field")

    def test_roundtrip_serialization_with_metadata(self):
        """Test that to_json and from_json are symmetric with metadata."""
        metadata = InstrumentMetadata(
            type="option",
            channel="quote.BTC-31JAN25-60000-P",
            currency="BTC",
            expiry="31JAN25",
            strike=60000.0,
            option_type="put",
        )
        original = SubscriptionUpdate(
            name="BTC-31JAN25-60000-P",
            subscription_type="instrument",
            action="subscribe",
            metadata=metadata,
            timestamp=1700000000,
        )

        json_str = original.to_json()
        restored = SubscriptionUpdate.from_json(json_str)

        assert restored.name == original.name
        assert restored.subscription_type == original.subscription_type
        assert restored.action == original.action
        assert restored.timestamp == original.timestamp
        assert isinstance(restored.metadata, InstrumentMetadata)


class TestPDFData:
    """Tests for PDFData dataclass."""

    def test_to_json(self):
        """Test converting PDF data to JSON."""
        data = PDFData(
            instrument="BTC-31JAN25-60000-C",
            currency="BTC",
            expiry_timestamp=1738368000,
            futures_price=65000.0,
            volatility=0.75,
            pdf_values=[0.1, 0.2, 0.3, 0.2, 0.1],
            timestamp=1700000000,
        )

        result = data.to_json()
        parsed = orjson.loads(result)

        assert parsed["instrument"] == "BTC-31JAN25-60000-C"
        assert parsed["currency"] == "BTC"
        assert parsed["expiry_timestamp"] == 1738368000
        assert parsed["futures_price"] == 65000.0
        assert parsed["volatility"] == 0.75
        assert parsed["pdf_values"] == [0.1, 0.2, 0.3, 0.2, 0.1]
        assert parsed["timestamp"] == 1700000000

    def test_to_json_default_timestamp(self):
        """Test that default timestamp is set when not provided."""
        data = PDFData(
            instrument="BTC-31JAN25-60000-C",
            currency="BTC",
            expiry_timestamp=1738368000,
            futures_price=65000.0,
            volatility=0.75,
            pdf_values=[0.1, 0.2, 0.3],
        )

        with patch("time.time", return_value=1700000000):
            result = data.to_json()
            parsed = orjson.loads(result)
            assert parsed["timestamp"] == 1700000000

    def test_from_json(self):
        """Test creating PDFData from JSON."""
        json_data = orjson.dumps(
            {
                "instrument": "BTC-31JAN25-60000-C",
                "currency": "BTC",
                "expiry_timestamp": 1738368000,
                "futures_price": 65000.0,
                "volatility": 0.75,
                "pdf_values": [0.1, 0.2, 0.3, 0.2, 0.1],
                "timestamp": 1700000000,
            }
        ).decode()

        result = PDFData.from_json(json_data)

        assert result.instrument == "BTC-31JAN25-60000-C"
        assert result.currency == "BTC"
        assert result.expiry_timestamp == 1738368000
        assert result.futures_price == 65000.0
        assert result.volatility == 0.75
        assert result.pdf_values == [0.1, 0.2, 0.3, 0.2, 0.1]
        assert result.timestamp == 1700000000

    def test_from_json_with_empty_pdf_values(self):
        """Test creating PDFData with empty pdf_values list."""
        json_data = orjson.dumps(
            {
                "instrument": "BTC-31JAN25-60000-C",
                "currency": "BTC",
                "expiry_timestamp": 1738368000,
                "futures_price": 65000.0,
                "volatility": 0.75,
                "pdf_values": [],
                "timestamp": 1700000000,
            }
        ).decode()

        result = PDFData.from_json(json_data)

        assert result.pdf_values == []

    def test_roundtrip_serialization(self):
        """Test that to_json and from_json are symmetric."""
        original = PDFData(
            instrument="BTC-31JAN25-60000-C",
            currency="BTC",
            expiry_timestamp=1738368000,
            futures_price=65000.0,
            volatility=0.75,
            pdf_values=[0.1, 0.2, 0.3, 0.2, 0.1],
            timestamp=1700000000,
        )

        json_str = original.to_json()
        restored = PDFData.from_json(json_str)

        assert restored.instrument == original.instrument
        assert restored.currency == original.currency
        assert restored.expiry_timestamp == original.expiry_timestamp
        assert restored.futures_price == original.futures_price
        assert restored.volatility == original.volatility
        assert restored.pdf_values == original.pdf_values
        assert restored.timestamp == original.timestamp

    def test_from_json_with_complex_pdf_values(self):
        """Test creating PDFData with complex PDF values array."""
        pdf_values = [i / 100.0 for i in range(100)]
        json_data = orjson.dumps(
            {
                "instrument": "ETH-28FEB25-3500-P",
                "currency": "ETH",
                "expiry_timestamp": 1740787200,
                "futures_price": 3500.0,
                "volatility": 0.85,
                "pdf_values": pdf_values,
                "timestamp": 1700000000,
            }
        ).decode()

        result = PDFData.from_json(json_data)

        assert len(result.pdf_values) == 100
        assert result.pdf_values == pdf_values
