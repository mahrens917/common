"""Settlement information fetcher."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from common.truthy import pick_if

from ..data_models.trading import OrderSide
from ..trading_exceptions import KalshiTradingError
from .market_scanner import MarketScanner
from .state_tracker import SettlementInfo
from .string_utils import coerce_optional_str

logger = logging.getLogger(__name__)

# Constants
_SETTLEMENT_THRESHOLD_CENTS = 50

TRADING_ERRORS = (
    KalshiTradingError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
)


# Constants
_CONST_50 = 50


class SettlementFetcher:
    """Fetches settlement information from market data."""

    def __init__(self, scanner: MarketScanner):
        """
        Initialize settlement fetcher.

        Args:
            scanner: Market scanner for data fetching
        """
        self.scanner = scanner
        # Cache of settlement info keyed by ticker for test verification.
        self.settlement_cache: dict[str, SettlementInfo] = {}

    async def fetch_settlement_info(self, ticker: str) -> Optional[SettlementInfo]:
        """
        Fetch settlement information for a market.

        Args:
            ticker: Market ticker

        Returns:
            Settlement info or None if not available
        """
        try:
            market_data = await self.scanner.fetch_market_data(ticker)
            if not market_data:
                return None

            status_raw = coerce_optional_str(market_data, "status")
            status = str(status_raw).lower()
            is_settled = status in ["settled", "resolved"]

            settlement_info = SettlementInfo(
                ticker=ticker,
                settlement_price_cents=(market_data["result_price"] if "result_price" in market_data else None),
                settlement_time=None,
                winning_side=None,
                is_settled=is_settled,
            )

            if is_settled and settlement_info.settlement_price_cents is not None:
                settlement_info.winning_side = pick_if(
                    settlement_info.settlement_price_cents >= _SETTLEMENT_THRESHOLD_CENTS,
                    lambda: OrderSide.YES.value,
                    lambda: OrderSide.NO.value,
                )
        except TRADING_ERRORS + (  # policy_guard: allow-silent-handler
            ValueError,
            KeyError,
        ):
            logger.exception(f"[SettlementFetcher] Error fetching settlement info for : ")
            return None
        else:
            return settlement_info
