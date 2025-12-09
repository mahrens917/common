"""Result building for market validation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..kalshi import KalshiMarketValidation


def build_failure_result(
    reason: str,
    expiry: Optional[datetime] = None,
    expiry_raw: Optional[str] = None,
    strike: Optional[float] = None,
    strike_type: Optional[str] = None,
    floor_strike: Optional[float] = None,
    cap_strike: Optional[float] = None,
) -> KalshiMarketValidation:
    """Build a validation failure result."""
    return KalshiMarketValidation(
        False,
        reason=reason,
        expiry=expiry,
        expiry_raw=expiry_raw,
        strike=strike,
        strike_type=strike_type,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
    )


@dataclass(frozen=True)
class MarketStrikeInfo:
    """Strike information for market validation."""

    expiry: datetime
    expiry_raw: str
    strike: float
    strike_type: str
    floor_strike: Optional[float]
    cap_strike: Optional[float]


@dataclass(frozen=True)
class MarketPricingInfo:
    """Pricing information for market validation."""

    bid_price: Optional[float]
    bid_size: Optional[int]
    ask_price: Optional[float]
    ask_size: Optional[int]
    has_orderbook: bool


def build_success_result(
    strike_info: MarketStrikeInfo,
    pricing_info: MarketPricingInfo,
) -> KalshiMarketValidation:
    """Build a validation success result."""
    from .pricing_validator import check_side_validity

    has_bid = check_side_validity(pricing_info.bid_price, pricing_info.bid_size)
    has_ask = check_side_validity(pricing_info.ask_price, pricing_info.ask_size)

    return KalshiMarketValidation(
        True,
        expiry=strike_info.expiry,
        expiry_raw=strike_info.expiry_raw,
        strike=strike_info.strike,
        strike_type=strike_info.strike_type,
        floor_strike=strike_info.floor_strike,
        cap_strike=strike_info.cap_strike,
        yes_bid_price=pricing_info.bid_price if has_bid else None,
        yes_bid_size=pricing_info.bid_size if has_bid else None,
        yes_ask_price=pricing_info.ask_price if has_ask else None,
        yes_ask_size=pricing_info.ask_size if has_ask else None,
        last_price=None,
        has_orderbook=pricing_info.has_orderbook,
    )
