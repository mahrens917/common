"""
Market Aggregator - Aggregate and collect market data

Handles market aggregation by strike/expiry points and summary building.
"""

from collections import defaultdict
from typing import Any, Dict, List, Sequence, Tuple

from common.exceptions import DataError

from .aggregator_utils import build_strike_summary


class MarketAggregator:
    """Aggregate market data by strike and expiry"""

    def aggregate_markets_by_point(
        self, markets: Sequence[Dict[str, Any]]
    ) -> Tuple[Dict[Tuple[str, float, str], List[str]], Dict[str, Dict[str, Any]]]:
        """
        Aggregate markets by (expiry, strike, strike_type) point

        Args:
            markets: List of market records

        Returns:
            Tuple of (grouped_markets, market_by_ticker)
            - grouped_markets: Dict mapping (expiry, strike, strike_type) to list of tickers
            - market_by_ticker: Dict mapping ticker to market record
        """
        grouped: Dict[Tuple[str, float, str], List[str]] = defaultdict(list)
        market_by_ticker: Dict[str, Dict[str, Any]] = {}
        for market in markets:
            expiry = market.get("expiry")
            strike = market.get("strike")
            strike_type_value = market.get("strike_type")
            ticker = market.get("market_ticker")
            if expiry is None or strike is None or not strike_type_value or not ticker:
                raise DataError(
                    f"Market {ticker} missing strike metadata " f"(expiry={expiry}, strike={strike}, strike_type={strike_type_value})"
                )
            try:
                strike_value = float(strike)
            except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
                raise RuntimeError(f"Market {ticker} has non-numeric strike value: {strike}") from exc
            strike_type = str(strike_type_value)
            ticker_str = str(ticker)
            grouped[(str(expiry), strike_value, strike_type)].append(ticker_str)
            market_by_ticker[ticker_str] = market
        return grouped, market_by_ticker

    def build_strike_summary(
        self,
        grouped: Dict[Tuple[str, float, str], List[str]],
        market_by_ticker: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Build strike summary from grouped markets."""
        return build_strike_summary(grouped, market_by_ticker)
