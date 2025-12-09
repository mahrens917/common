"""
Message structures and serialization for Redis communication
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Union

import orjson

from src.common.exceptions import ValidationError

from .messages_helpers.field_validator import validate_float_field, validate_required_field
from .messages_helpers.option_normalizer import normalize_option_type
from .messages_helpers.timestamp_converter import format_utc_timestamp, parse_utc_timestamp

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data message"""

    instrument: str
    currency: str  # 'BTC' or 'ETH'
    strike_price: float
    expiry_timestamp: int
    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    instrument_type: str = "option"
    option_type: Optional[str] = None
    timestamp: int = 0

    def to_redis_hash(self) -> dict:
        """Convert to Redis hash fields"""
        # Always include market data
        result = {
            "best_bid": str(self.best_bid),
            "best_ask": str(self.best_ask),
            "best_bid_size": str(self.best_bid_size),
            "best_ask_size": str(self.best_ask_size),
            "last_update": format_utc_timestamp(self.timestamp or int(time.time())),
        }

        try:
            expiry_dt = datetime.fromtimestamp(self.expiry_timestamp, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise ValidationError(f"Invalid expiry_timestamp for {self.instrument}") from exc

        instrument_type_label = "Option" if self.instrument_type.lower() == "option" else "Future"

        result.update(
            {
                "currency": self.currency,
                "expiry_date": expiry_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "instrument_type": instrument_type_label,
            }
        )

        if self.instrument_type.lower() == "option":
            result["strike_price"] = str(float(self.strike_price))
            option_type_normalized = normalize_option_type(self.option_type)
            if option_type_normalized:
                result["option_type"] = option_type_normalized
        elif "strike_price" not in result:
            result["strike_price"] = str(float(self.strike_price))

        return result

    @classmethod
    def from_redis_hash(cls, instrument: str, hash_data: dict) -> "MarketData":
        """Create from Redis hash data and instrument name"""
        # Parse timestamps
        expiry_date = validate_required_field(hash_data, "expiry_date", "market data")
        expiry_timestamp = parse_utc_timestamp(expiry_date)

        last_update = validate_required_field(hash_data, "last_update", "market data")
        timestamp = parse_utc_timestamp(last_update)

        # Validate required fields
        currency = validate_required_field(hash_data, "currency", "market data")
        instrument_type_field = validate_required_field(hash_data, "instrument_type", "market data")

        # Validate numeric fields
        strike_price = validate_float_field(hash_data, "strike_price", "market data")
        best_bid = validate_float_field(hash_data, "best_bid", "market data")
        best_ask = validate_float_field(hash_data, "best_ask", "market data")
        best_bid_size = validate_float_field(hash_data, "best_bid_size", "market data")
        best_ask_size = validate_float_field(hash_data, "best_ask_size", "market data")

        # Optional field
        option_type_field = hash_data.get("option_type")

        return cls(
            instrument=instrument,
            currency=currency,
            strike_price=strike_price,
            expiry_timestamp=expiry_timestamp,
            best_bid=best_bid,
            best_ask=best_ask,
            best_bid_size=best_bid_size,
            best_ask_size=best_ask_size,
            instrument_type=instrument_type_field.lower(),
            option_type=normalize_option_type(option_type_field),
            timestamp=timestamp,
        )


@dataclass
class PriceIndexData:
    """Price index data message"""

    index_name: str  # e.g. "btc_usd"
    price: float
    timestamp: int = 0  # milliseconds since epoch

    def to_redis_hash(self) -> dict:
        """Convert to Redis hash fields"""
        timestamp_seconds = self.timestamp / 1000 if self.timestamp else time.time()
        return {
            "value": str(self.price),
            "last_update": format_utc_timestamp(int(timestamp_seconds)),
        }

    @classmethod
    def from_redis_hash(cls, index_name: str, hash_data: dict) -> "PriceIndexData":
        """Create from Redis hash data"""
        last_update = validate_required_field(hash_data, "last_update", "market data")
        timestamp = parse_utc_timestamp(last_update) * 1000  # Convert to milliseconds

        # Try both 'value' and 'price' fields
        price_value = hash_data.get("value") or hash_data.get("price")
        if price_value is None:
            raise RuntimeError(
                "Missing required price field (tried both 'value' and 'price') - no default values allowed"
            )
        price = float(price_value)

        return cls(index_name=index_name, price=price, timestamp=timestamp)


@dataclass
class VolatilityIndexData:
    """Volatility index data message"""

    index_name: str  # e.g. "btc_usd"
    volatility: float
    timestamp: int = 0  # milliseconds since epoch

    def to_redis_hash(self) -> dict:
        """Convert to Redis hash fields"""
        timestamp_seconds = self.timestamp / 1000 if self.timestamp else time.time()
        return {
            "volatility": str(self.volatility),
            "last_update": format_utc_timestamp(int(timestamp_seconds)),
        }

    @classmethod
    def from_redis_hash(cls, index_name: str, hash_data: dict) -> "VolatilityIndexData":
        """Create from Redis hash data"""
        last_update = validate_required_field(hash_data, "last_update", "market data")
        timestamp = parse_utc_timestamp(last_update) * 1000  # Convert to milliseconds

        volatility = validate_float_field(hash_data, "volatility", "volatility data")

        return cls(index_name=index_name, volatility=volatility, timestamp=timestamp)


@dataclass
class InstrumentMetadata:
    """Metadata for instrument subscriptions"""

    type: str  # 'option' or 'future'
    channel: str  # Full channel name (e.g. 'quote.BTC-31JAN25-60000-P')
    currency: str  # 'BTC' or 'ETH'
    expiry: str  # Expiry date (e.g. '31JAN25')
    strike: float = 0.0  # Strike price (for options)
    option_type: str = ""  # 'call' or 'put' (for options)
    expiry_timestamp: Optional[int] = None
    redis_key: str = ""

    def to_json(self) -> str:
        """Convert to JSON string"""
        from typing import Any, Dict

        data: Dict[str, Any] = {
            "type": self.type,
            "channel": self.channel,
            "currency": self.currency,
            "expiry": self.expiry,
        }
        if self.type == "option":
            data.update({"strike": self.strike, "option_type": self.option_type})
        return orjson.dumps(data).decode()

    @classmethod
    def from_json(cls, data: str) -> "InstrumentMetadata":
        """Create from JSON string"""
        return cls(**orjson.loads(data))


@dataclass
class IndexMetadata:
    """Metadata for index subscriptions"""

    channel: str  # Full channel name (e.g. 'deribit_price_index.btc_usd')

    def to_json(self) -> str:
        """Convert to JSON string"""
        return orjson.dumps({"channel": self.channel}).decode()

    @classmethod
    def from_json(cls, data: str) -> "IndexMetadata":
        """Create from JSON string"""
        return cls(**orjson.loads(data))


@dataclass
class SubscriptionUpdate:
    """Subscription update message"""

    name: str  # Instrument name or index name
    subscription_type: str  # 'instrument', 'price_index', or 'volatility_index'
    action: str  # 'subscribe' or 'unsubscribe'
    metadata: Union[InstrumentMetadata, IndexMetadata, None] = None  # Subscription metadata
    timestamp: int = 0

    def to_json(self) -> str:
        """Convert to JSON string"""
        if self.metadata is None:
            metadata_payload: dict[str, Any] = {}
        else:
            metadata_payload = orjson.loads(self.metadata.to_json())

        return orjson.dumps(
            {
                "name": self.name,
                "subscription_type": self.subscription_type,
                "action": self.action,
                "metadata": metadata_payload,
                "timestamp": self.timestamp or int(time.time()),
            }
        ).decode()

    @classmethod
    def from_json(cls, data: str) -> "SubscriptionUpdate":
        """Create from JSON string"""
        data_dict = orjson.loads(data)
        metadata_dict = data_dict.pop("metadata", None)

        # Create appropriate metadata object based on subscription type
        metadata: Union[InstrumentMetadata, IndexMetadata, None]
        if metadata_dict is None:
            metadata = None
        elif data_dict["subscription_type"] == "instrument":
            metadata = InstrumentMetadata(**metadata_dict)
        else:
            filtered_metadata = {k: v for k, v in metadata_dict.items() if k in ["channel"]}
            metadata = IndexMetadata(**filtered_metadata)

        data_dict["metadata"] = metadata
        return cls(**data_dict)


@dataclass
class PDFData:
    """PDF data message"""

    instrument: str
    currency: str
    expiry_timestamp: int
    futures_price: float
    volatility: float
    pdf_values: list
    timestamp: int = 0

    def to_json(self) -> str:
        """Convert to JSON string"""
        return orjson.dumps(
            {
                "instrument": self.instrument,
                "currency": self.currency,
                "expiry_timestamp": self.expiry_timestamp,
                "futures_price": self.futures_price,
                "volatility": self.volatility,
                "pdf_values": self.pdf_values,
                "timestamp": self.timestamp or int(time.time()),
            }
        ).decode()

    @classmethod
    def from_json(cls, data: str) -> "PDFData":
        """Create from JSON string"""
        return cls(**orjson.loads(data))
