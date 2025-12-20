"""Weather market fetching logic."""

from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class WeatherFetcher:
    """Fetches weather-specific markets."""

    def __init__(self, client, fetcher_client):
        """Initialize with client."""
        self._client = client
        self._fetcher_client = fetcher_client

    async def fetch_weather_markets(
        self, category: str, markets: List[Dict[str, object]], seen_tickers: set[str]
    ) -> int:
        """Fetch weather-specific markets."""
        from common.kalshi_api import KalshiClientError
        from ..market_fetcher import KalshiMarketCatalogError

        try:
            series_list = await self._client.get_series(category=category)
        except (KalshiClientError, KeyError, TypeError, ValueError, Exception) as exc:
            raise KalshiMarketCatalogError(
                f"Failed to fetch Kalshi weather series for {category}"
            ) from exc

        pages = 0
        matched_series = 0
        for series in series_list:
            ticker = series.get("ticker") if isinstance(series, dict) else None
            if not ticker or not ticker.upper().startswith("KXHIGH"):
                continue

            matched_series += 1
            pages += await self._fetcher_client.fetch_markets(
                f"series {ticker}",
                markets,
                seen_tickers,
                base_params={"category": category, "series_ticker": ticker},
            )

        if matched_series == 0:
            raise KalshiMarketCatalogError(
                f"Weather series for {category} returned no KXHIGH tickers"
            )
        return pages
