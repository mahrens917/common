"""Add markets to list with deduplication."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MarketAdder:
    """Adds markets to list, handling deduplication."""

    @staticmethod
    def add_markets(
        page_markets: List[Any],
        markets: List[Dict[str, object]],
        seen_tickers: set[str],
        label: str,
        base_params: Optional[Dict[str, Optional[str]]],
    ) -> int:
        """Add markets from page to list, deduplicating by ticker."""
        from ..market_fetcher import KalshiMarketCatalogError

        added = 0
        for market in page_markets:
            ticker = market.get("ticker") if isinstance(market, dict) else None
            if not isinstance(ticker, str) or not ticker.strip():
                raise KalshiMarketCatalogError("Kalshi market missing ticker")
            ticker_upper = ticker.upper()
            if ticker_upper in seen_tickers:
                continue
            if ticker != ticker_upper:
                market["ticker"] = ticker_upper
            seen_tickers.add(ticker_upper)
            category = base_params.get("category") if base_params else None
            market["__category"] = category if category else label
            markets.append(market)
            added += 1
        return added
