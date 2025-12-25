from __future__ import annotations

"""Market discovery utilities for the Kalshi websocket service."""


import logging
from pathlib import Path
from typing import Dict, List

from common.kalshi_api import KalshiClient
from common.redis_protocol.messages import InstrumentMetadata

from .kalshi_catalog_helpers import MarketFetcher, MarketFilter, WeatherStationLoader

logger = logging.getLogger(__name__)


class KalshiMarketCatalogError(RuntimeError):
    """Raised when market discovery fails."""


class KalshiMarketCatalog:
    """Fetch and filter Kalshi markets for websocket subscriptions."""

    _DEFAULT_REFRESH_INTERVAL_SECONDS: int = 900
    _DEFAULT_MARKET_STATUS: str = "open"
    _DEFAULT_MARKET_CATEGORIES: tuple[str, ...] = ("Crypto", "Climate and Weather")
    _CRYPTO_ASSETS: tuple[str, ...] = ("BTC", "ETH")

    def __init__(self, client: KalshiClient) -> None:
        self._client = client
        from src.kalshi.settings import get_kalshi_settings

        settings = get_kalshi_settings().market_catalog

        self._refresh_interval_seconds = max(1, settings.refresh_interval_seconds)

        if settings.categories is None:
            self._market_categories = None
        else:
            self._market_categories = settings.categories

        status_value = settings.status
        self._market_status = status_value if status_value else self._DEFAULT_MARKET_STATUS

        # Initialize helpers
        config_root = Path(__file__).resolve().parents[2] / "config"
        station_loader = WeatherStationLoader(config_root)
        weather_station_tokens = station_loader.load_station_tokens()

        self._market_fetcher = MarketFetcher(client, self._market_status, self._CRYPTO_ASSETS)
        self._market_filter = MarketFilter(weather_station_tokens)

    @property
    def refresh_interval_seconds(self) -> int:
        """Return the configured refresh interval for market scans."""
        return self._refresh_interval_seconds

    async def fetch_markets(self) -> List[Dict[str, object]]:
        """Fetch and return the filtered set of Kalshi markets."""
        markets, total_pages = await self._market_fetcher.fetch_all_markets(self._market_categories)

        category_summary = ",".join(self._market_categories) if self._market_categories else "<all>"
        logger.info(
            "Kalshi market fetch complete: %s markets across %s page(s) (categories=%s)",
            len(markets),
            total_pages,
            category_summary,
        )

        filtered_markets, stats = self._market_filter.filter_markets(markets)

        if not filtered_markets:
            raise KalshiMarketCatalogError("No eligible Kalshi markets returned after filtering")

        logger.info(
            "Kalshi market filter summary: crypto %s/%s kept, weather %s/%s kept, other discarded=%s",
            stats["crypto_kept"],
            stats["crypto_total"],
            stats["weather_kept"],
            stats["weather_total"],
            stats["other_total"],
        )

        return filtered_markets

    async def fetch_metadata(self) -> Dict[str, InstrumentMetadata]:
        """Fetch markets and return their subscription metadata."""
        filtered_markets = await self.fetch_markets()
        return self._metadata_from_markets(filtered_markets)

    def build_metadata(self, markets: List[Dict[str, object]]) -> Dict[str, InstrumentMetadata]:
        """Build metadata map from an already filtered set of markets."""
        if not markets:
            raise KalshiMarketCatalogError("Cannot build metadata from empty market list")
        return self._metadata_from_markets(markets)

    def _metadata_from_markets(self, markets: List[Dict[str, object]]) -> Dict[str, InstrumentMetadata]:
        """Convert markets to metadata map."""
        metadata: Dict[str, InstrumentMetadata] = {}
        for market in markets:
            ticker = market["ticker"] if "ticker" in market else None
            if not isinstance(ticker, str):
                raise KalshiMarketCatalogError("Kalshi market missing ticker")

            raw_currency = market.get("currency")
            currency_value = str(raw_currency) if raw_currency is not None else "unknown"

            raw_close_time = market.get("close_time")
            close_time_text = str(raw_close_time) if raw_close_time is not None else ""

            metadata[ticker] = InstrumentMetadata(
                type="market",
                channel=f"market.{ticker}",
                currency=currency_value,
                expiry=close_time_text,
            )
        return metadata
