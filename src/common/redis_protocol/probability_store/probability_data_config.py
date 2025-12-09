"""Configuration dataclass for probability storage parameters."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ProbabilityData:
    """Configuration for storing a single probability entry."""

    currency: str
    expiry: str
    strike_type: str
    strike: float
    probability: float
    error: Optional[float] = None
    confidence: Optional[float] = None
    probability_range: Optional[Tuple[float, float]] = None
