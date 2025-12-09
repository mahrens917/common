"""
Data models for market data structures.

Contains dataclass definitions for various market data types used throughout
the application, including Deribit futures and options data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .micro_price_helpers.calculations import MicroPriceCalculator
from .micro_price_helpers.validation import MicroPriceValidator
from .micro_price_helpers.validation_params import (
    BasicOptionData,
    MathematicalRelationships,
    ValidationErrorParams,
)
from .micropriceoptiondata_helpers.factory import MicroPriceOptionDataFactory
from .micropriceoptiondata_helpers.properties import MicroPriceProperties


@dataclass
class DeribitFuturesData:
    """Data structure for Deribit futures market data"""

    instrument_name: str
    underlying: str
    expiry_timestamp: int
    bid_price: float
    ask_price: float
    best_bid_size: float
    best_ask_size: float
    timestamp: datetime

    # Optional fields that may be present in real data
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    index_price: Optional[float] = None
    open_interest: Optional[float] = None
    volume_24h: Optional[float] = None

    def __post_init__(self):
        """Validate data after initialization"""
        if self.bid_price < 0:
            raise ValueError(f"Bid price cannot be negative: {self.bid_price}")
        if self.ask_price < 0:
            raise ValueError(f"Ask price cannot be negative: {self.ask_price}")
        if self.ask_price < self.bid_price:
            raise ValueError(
                f"Ask price ({self.ask_price}) must be >= bid price ({self.bid_price})"
            )
        if self.best_bid_size < 0:
            raise ValueError(f"Bid size cannot be negative: {self.best_bid_size}")
        if self.best_ask_size < 0:
            raise ValueError(f"Ask size cannot be negative: {self.best_ask_size}")

        # Set best_bid/best_ask if not provided
        if self.best_bid is None:
            self.best_bid = self.bid_price
        if self.best_ask is None:
            self.best_ask = self.ask_price


@dataclass
class DeribitOptionData:
    """Data structure for Deribit options market data"""

    instrument_name: str
    underlying: str
    strike: float
    expiry_timestamp: int
    option_type: str  # "call" or "put"
    bid_price: float
    ask_price: float
    best_bid_size: float
    best_ask_size: float
    timestamp: datetime

    # Optional fields that may be present in real data
    index_price: Optional[float] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    open_interest: Optional[float] = None
    volume_24h: Optional[float] = None

    # CF conversion metadata
    cf_conversion_applied: bool = False
    cf_conversion_factor: Optional[float] = None

    def __post_init__(self):
        """Validate data after initialization"""
        if self.strike <= 0:
            raise ValueError(f"Strike price must be positive: {self.strike}")
        if self.bid_price < 0:
            raise ValueError(f"Bid price cannot be negative: {self.bid_price}")
        if self.ask_price < 0:
            raise ValueError(f"Ask price cannot be negative: {self.ask_price}")
        if self.ask_price < self.bid_price:
            raise ValueError(
                f"Ask price ({self.ask_price}) must be >= bid price ({self.bid_price})"
            )


@dataclass(frozen=True)
class MicroPriceMetrics:
    """Captures intermediate micro price calculations."""

    absolute_spread: float
    relative_spread: float
    i_raw: float
    p_raw: float
    g: float
    h: float


class MicroPriceOptionDataMixin:
    """Shared helpers for micro price option data computations and validations."""

    best_bid: float
    best_ask: float
    absolute_spread: float
    i_raw: float
    p_raw: float
    best_bid_size: float
    best_ask_size: float
    option_type: str
    strike: float
    expiry: datetime

    def validate_micro_price_constraints(self) -> bool:
        return MicroPriceValidator.validate_micro_price_constraints(
            self.best_bid, self.best_ask, self.absolute_spread, self.i_raw, self.p_raw
        )

    def is_valid(self) -> bool:
        params = ValidationErrorParams(
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            best_bid_size=self.best_bid_size,
            best_ask_size=self.best_ask_size,
            option_type=self.option_type,
            absolute_spread=self.absolute_spread,
            i_raw=self.i_raw,
            p_raw=self.p_raw,
        )
        errors = MicroPriceValidator.get_validation_errors(params)
        return len(errors) == 0

    def get_validation_errors(self) -> List[str]:
        params = ValidationErrorParams(
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            best_bid_size=self.best_bid_size,
            best_ask_size=self.best_ask_size,
            option_type=self.option_type,
            absolute_spread=self.absolute_spread,
            i_raw=self.i_raw,
            p_raw=self.p_raw,
        )
        return MicroPriceValidator.get_validation_errors(params)

    def intrinsic_value(self, spot_price: float) -> float:
        return MicroPriceCalculator.compute_intrinsic_value(
            self.option_type, self.strike, spot_price
        )

    def time_value(self, spot_price: float) -> float:
        return MicroPriceCalculator.compute_time_value(
            self.option_type, self.strike, spot_price, self.p_raw
        )

    @classmethod
    def from_enhanced_option_data(cls, enhanced_option):
        return MicroPriceOptionDataFactory.from_enhanced_option_data(enhanced_option, cls)

    @property
    def is_future(self) -> bool:
        return MicroPriceProperties.get_is_future()

    @property
    def expiry_timestamp(self) -> int:
        return MicroPriceProperties.get_expiry_timestamp(self.expiry)

    @property
    def bid_price(self) -> float:
        return MicroPriceProperties.get_bid_price(self.best_bid)

    @property
    def ask_price(self) -> float:
        return MicroPriceProperties.get_ask_price(self.best_ask)

    @property
    def mid_price(self) -> float:
        return MicroPriceProperties.get_mid_price(self.best_bid, self.best_ask)

    @property
    def spread(self) -> float:
        return MicroPriceProperties.get_spread(self.absolute_spread)

    @property
    def is_call(self) -> bool:
        return MicroPriceProperties.check_is_call(self.option_type)

    @property
    def is_put(self) -> bool:
        return MicroPriceProperties.check_is_put(self.option_type)


@dataclass
class MicroPriceOptionData(MicroPriceOptionDataMixin):
    """Deribit options with micro price calculations (g, h transformations for GP)."""

    instrument_name: str
    underlying: str
    strike: float
    expiry: datetime
    option_type: str
    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    timestamp: datetime
    absolute_spread: float
    relative_spread: float
    i_raw: float
    p_raw: float
    g: float
    h: float
    forward_price: Optional[float] = None
    discount_factor: Optional[float] = None
    quote_age_seconds: Optional[float] = None
    index_price: Optional[float] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    open_interest: Optional[float] = None
    volume_24h: Optional[float] = None

    def __post_init__(self) -> None:
        basic_data = BasicOptionData(
            strike=self.strike,
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            best_bid_size=self.best_bid_size,
            best_ask_size=self.best_ask_size,
            option_type=self.option_type,
            forward_price=self.forward_price,
            discount_factor=self.discount_factor,
        )
        MicroPriceValidator.validate_basic_option_data(basic_data)
        MicroPriceValidator.validate_micro_price_calculations(
            self.absolute_spread, self.i_raw, self.p_raw
        )

        math_relationships = MathematicalRelationships(
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            best_bid_size=self.best_bid_size,
            best_ask_size=self.best_ask_size,
            absolute_spread=self.absolute_spread,
            relative_spread=self.relative_spread,
            i_raw=self.i_raw,
            p_raw=self.p_raw,
            g=self.g,
            h=self.h,
        )
        MicroPriceValidator.validate_mathematical_relationships(math_relationships)


@dataclass
class Instrument:
    """Generic instrument data structure"""

    instrument_name: str
    underlying: str
    expiry_timestamp: int
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    last_price: Optional[float] = None
    best_bid_size: Optional[float] = None
    best_ask_size: Optional[float] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Validate data after initialization"""
        if self.bid_price is not None and self.bid_price < 0:
            raise ValueError(f"Bid price cannot be negative: {self.bid_price}")
        if self.ask_price is not None and self.ask_price < 0:
            raise ValueError(f"Ask price cannot be negative: {self.ask_price}")
        if (
            self.bid_price is not None
            and self.ask_price is not None
            and self.ask_price < self.bid_price
        ):
            raise ValueError(
                f"Ask price ({self.ask_price}) must be >= bid price ({self.bid_price})"
            )
