"""Market state tracking and settlement information."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from .expiry_checker import ExpiryChecker
from .market_scanner import MarketScanner
from .string_utils import coerce_optional_str


class MarketState(Enum):
    """Market lifecycle states."""

    ACTIVE = "active"
    CLOSING_SOON = "closing_soon"
    CLOSED = "closed"
    SETTLING = "settling"
    SETTLED = "settled"
    UNKNOWN = "unknown"


@dataclass
class MarketInfo:
    """Market information for lifecycle monitoring."""

    ticker: str
    title: str
    close_time: Optional[datetime]
    status: str
    state: MarketState
    time_to_close_hours: float

    def __post_init__(self):
        if not self.ticker:
            raise ValueError("Ticker cannot be empty")


@dataclass
class SettlementInfo:
    """Settlement information tracked for each monitored market."""

    ticker: str
    settlement_price_cents: Optional[int]
    settlement_time: Optional[datetime]
    winning_side: Optional[str]
    is_settled: bool


class StateTracker:
    """Tracks market states and settlement information."""

    def __init__(self, scanner: MarketScanner, expiry_checker: ExpiryChecker):
        """
        Initialize state tracker.

        Args:
            scanner: Market scanner for data fetching
            expiry_checker: Expiry checker for time calculations
        """
        self.scanner = scanner
        self.expiry_checker = expiry_checker
        self.monitored_markets: Dict[str, MarketInfo] = {}
        self.settlement_cache: Dict[str, SettlementInfo] = {}

    def parse_market_info(self, market_data: Dict[str, Any]) -> MarketInfo:
        """
        Parse market data into MarketInfo object.

        Args:
            market_data: Raw market data from API

        Returns:
            Parsed MarketInfo
        """
        ticker = market_data["ticker"]
        title = coerce_optional_str(market_data, "title")

        close_time = self.expiry_checker.parse_close_time(market_data)
        time_to_close_hours = self.expiry_checker.calculate_time_to_close_hours(close_time)

        status_raw = coerce_optional_str(market_data, "status")
        status = str(status_raw).lower()

        state = self._determine_state(status, time_to_close_hours)

        return MarketInfo(
            ticker=ticker,
            title=title,
            close_time=close_time,
            status=status,
            state=state,
            time_to_close_hours=max(0, time_to_close_hours),
        )

    def _determine_state(self, status: str, time_to_close_hours: float) -> MarketState:
        """Determine market state from status and time."""
        if status in ["settled", "resolved"]:
            return MarketState.SETTLED
        elif status == "closed":
            return MarketState.CLOSED
        elif time_to_close_hours <= 0:
            return MarketState.CLOSED
        elif self.expiry_checker.is_closing_soon(time_to_close_hours):
            return MarketState.CLOSING_SOON
        elif status in ["active", "open"]:
            return MarketState.ACTIVE
        else:
            return MarketState.UNKNOWN
