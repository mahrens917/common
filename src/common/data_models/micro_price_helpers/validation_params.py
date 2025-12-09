"""Parameter dataclasses for micro price validation functions."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BasicOptionData:
    """Basic option data parameters for validation."""

    strike: float
    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    option_type: str
    forward_price: Optional[float] = None
    discount_factor: Optional[float] = None


@dataclass
class MathematicalRelationships:
    """Mathematical relationships for validation."""

    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    absolute_spread: float
    relative_spread: float
    i_raw: float
    p_raw: float
    g: float
    h: float


@dataclass
class ValidationErrorParams:
    """Parameters for validation error collection."""

    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    option_type: str
    absolute_spread: float
    i_raw: float
    p_raw: float


@dataclass
class PostInitValidationParams:
    """Complete set of parameters for post-init validation."""

    strike: float
    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    option_type: str
    forward_price: float
    discount_factor: float
    absolute_spread: float
    relative_spread: float
    i_raw: float
    p_raw: float
    g: float
    h: float
