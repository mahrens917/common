"""Crypto market fetching logic."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class CryptoFetcher:
    """Fetches crypto-specific markets."""

    def __init__(self, client, crypto_assets: tuple[str, ...], fetcher_client):
        """Initialize with client and crypto assets."""
        self._client = client
        self._crypto_assets = crypto_assets
        self._fetcher_client = fetcher_client

    async def fetch_crypto_markets(
        self, markets: List[Dict[str, object]], seen_tickers: set[str]
    ) -> int:
        """Fetch crypto-specific markets."""
        from common.kalshi_api import KalshiClientError
        from ..market_fetcher import KalshiMarketCatalogError

        try:
            series_list = await self._client.get_series(category="Crypto")
        except (KalshiClientError, KeyError, TypeError, ValueError, Exception) as exc:
            raise KalshiMarketCatalogError(f"Failed to fetch Kalshi crypto series") from exc

        pages = 0
        matched_series = 0
        for series in series_list:
            ticker = series.get("ticker") if isinstance(series, dict) else None
            if not ticker:
                continue
            ticker_upper = ticker.upper()
            if not any(asset in ticker_upper for asset in self._crypto_assets):
                continue
            matched_series += 1

            pages += await self._fetcher_client.fetch_markets(
                f"series {ticker}",
                markets,
                seen_tickers,
                base_params={"category": "Crypto", "series_ticker": ticker},
            )

        if matched_series == 0:
            raise KalshiMarketCatalogError("Crypto series returned no BTC/ETH tickers")
        return pages
