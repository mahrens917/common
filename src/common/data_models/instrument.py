"""
Centralized Instrument dataclass for market data.

This module provides a unified Instrument dataclass for representing financial
instruments with market data. All modules should import from this location
to maintain consistency and avoid circular dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, cast


@dataclass
class Instrument:
    """
    Represents a financial instrument with market data.

    This dataclass contains all essential fields for representing options,
    futures, and other financial instruments with their current market data.
    Consumers must provide the canonical instrument name and expiry timestamp.
    """

    # Core identification fields
    instrument_name: str
    expiry: Optional[datetime | str | int | float]
    currency: Optional[str] = None

    # Option-specific fields
    strike: Optional[float] = None
    option_type: Optional[str] = None  # 'call' or 'put'
    is_future: Optional[bool] = None
    is_synthetic: Optional[bool] = (
        None  # True for synthetic calls created from puts via put-call parity
    )

    # Market data fields
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    price: Optional[float] = None
    best_bid_size: Optional[float] = None
    best_ask_size: Optional[float] = None
    implied_volatility: Optional[float] = None
    quote_timestamp: Optional[datetime] = None
    mark_price_timestamp: Optional[datetime] = None

    # Micro-price calculation fields
    i_raw: Optional[float] = None  # Raw intensity (mid - bid) / spread
    h: Optional[float] = None  # Logit intensity log(i_raw/(1-i_raw))
    s_raw: Optional[float] = None  # Raw spread (ask - bid)
    g: Optional[float] = None  # Log spread log(s_raw)
    p_raw: Optional[float] = None  # Raw micro price

    # CF conversion metadata
    cf_conversion_applied: bool = False
    cf_conversion_factor: Optional[float] = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.instrument_name.strip():
            raise ValueError("instrument_name must be a non-empty string")

        if self.expiry is None:
            raise ValueError("expiry must be provided")

        if not isinstance(cast(object, self.expiry), (datetime, str, int, float)):
            raise TypeError(
                f"expiry must be datetime, str, int, or float, got {type(self.expiry).__name__}"
            )

    @property
    def expiry_timestamp(self) -> int:
        """
        Get the expiry timestamp as an integer.

        This property provides compatibility with test code that expects
        'expiry_timestamp' attribute. Converts the datetime expiry to
        a Unix timestamp.

        Returns:
            int: The expiry timestamp
        """
        if self.expiry is None:
            raise ValueError("Expiry is None, cannot get timestamp")
        if isinstance(self.expiry, datetime):
            return int(self.expiry.timestamp())
        if isinstance(self.expiry, (int, float)):
            return int(self.expiry)
        # Handle string representations lazily
        expiry_str = self.expiry.replace("Z", "+00:00")
        try:
            return int(datetime.fromisoformat(expiry_str).timestamp())
        except ValueError as exc:  # pragma: no cover - compatibility guard
            raise ValueError(f"Invalid expiry string: {self.expiry}") from exc
