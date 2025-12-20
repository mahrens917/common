from __future__ import annotations

"""Market fetching with pagination for Kalshi catalog."""

import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

BaseParams = Dict[str, Optional[str]]


class KalshiMarketCatalogError(RuntimeError):
    """Raised when market discovery fails."""


def _build_request_params(
    client,
    base_params: Optional[BaseParams],
    cursor: Optional[str],
) -> BaseParams:
    params: Dict[str, Optional[str]] = dict(base_params) if base_params else {}
    params["status"] = client._market_status
    if cursor:
        params["cursor"] = cursor
    return params


async def _fetch_page(client, params: Dict[str, Optional[str]]) -> Dict[str, object]:
    from common.kalshi_api import KalshiClientError

    try:
        payload = await client.api_request(
            method="GET",
            path="/trade-api/v2/markets",
            params=params,
            operation_name="fetch_markets",
        )
    except KalshiClientError as exc:
        raise KalshiMarketCatalogError("Kalshi market request failed") from exc

    if not isinstance(payload, dict):
        raise KalshiMarketCatalogError("Kalshi markets payload was not a JSON object")
    return payload


def _extract_page_markets(payload: Dict[str, object]) -> List[Any]:
    page_markets = payload.get("markets")
    if not isinstance(page_markets, list):
        raise KalshiMarketCatalogError("Kalshi markets payload missing 'markets'")
    return page_markets


def _should_continue_pagination(cursor: Optional[str], seen_cursors: set[str | None], label: str) -> bool:
    if cursor in seen_cursors:
        logger.warning("Received repeated cursor '%s' for %s; stopping pagination", cursor, label)
        return False
    return True


def _extract_next_cursor(payload: Dict[str, object]) -> Optional[str]:
    cursor_val = payload.get("cursor")
    if cursor_val is None or not isinstance(cursor_val, str) or not cursor_val.strip():
        return None
    return cursor_val


def _add_markets(
    page_markets: List[Any],
    markets: List[Dict[str, object]],
    seen_tickers: set[str],
    label: str,
    base_params: Optional[Dict[str, Optional[str]]],
) -> int:
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


class MarketFetcherClient:
    """Encapsulates market fetching operations."""

    def __init__(self, client):
        self._client = client

    async def fetch_markets(
        self,
        label: str,
        markets: List[Dict[str, object]],
        seen_tickers: set[str],
        base_params: Optional[BaseParams],
    ) -> int:
        """Fetch markets with pagination."""
        cursor: str | None = None
        seen_cursors: set[str | None] = set()
        logged_params = base_params if base_params else "<none>"
        logger.info("Requesting Kalshi markets with params %s", logged_params)
        pages = 0

        while True:
            if not _should_continue_pagination(cursor, seen_cursors, label):
                break

            seen_cursors.add(cursor)
            params = _build_request_params(self._client, base_params, cursor)
            payload = await _fetch_page(self._client, params)
            page_markets = _extract_page_markets(payload)

            added = _add_markets(page_markets, markets, seen_tickers, label, base_params)
            logger.info(
                "Kalshi market page fetched: added=%s (raw page size=%s, accumulated=%s, label=%s)",
                added,
                len(page_markets),
                len(markets),
                label,
            )

            cursor = _extract_next_cursor(payload)
            if cursor is None:
                break
            pages += 1

        return pages


class MarketFetcher:
    """Fetches markets from Kalshi API with pagination."""

    _CRYPTO_ASSETS: tuple[str, ...] = ("BTC", "ETH")

    def __init__(self, client, market_status: str, crypto_assets: tuple[str, ...]) -> None:
        self._client = client
        self._client._market_status = market_status
        self._crypto_assets = crypto_assets
        self._fetcher_client = MarketFetcherClient(client)

    async def fetch_all_markets(self, categories: Optional[Iterable[str]]) -> tuple[List[Dict[str, object]], int]:
        """Fetch all markets across categories."""
        markets: List[Dict[str, object]] = []
        seen_tickers: set[str] = set()
        category_list: Iterable[Optional[str]] = categories if categories else (None,)
        total_pages = 0
        for category in category_list:
            if category == "Crypto":
                total_pages += await self._fetch_crypto_markets(markets, seen_tickers)
            elif category in {"Weather", "Climate and Weather"}:
                total_pages += await self._fetch_weather_markets(category, markets, seen_tickers)
            else:
                label = category if category else "<all>"
                base_params: BaseParams | None = {"category": category} if category else None
                total_pages += await self._fetcher_client.fetch_markets(label, markets, seen_tickers, base_params=base_params)
        return markets, total_pages

    async def _fetch_crypto_markets(self, markets: List[Dict[str, object]], seen_tickers: set[str]) -> int:
        """Fetch crypto-specific markets."""
        from common.kalshi_api import KalshiClientError

        try:
            series_list = await self._client.get_series(category="Crypto")
        except (KalshiClientError, KeyError, TypeError, ValueError) as exc:
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

            crypto_params: BaseParams = {"category": "Crypto", "series_ticker": ticker}
            pages += await self._fetcher_client.fetch_markets(
                f"series {ticker}",
                markets,
                seen_tickers,
                base_params=crypto_params,
            )

        if matched_series == 0:
            raise KalshiMarketCatalogError("Crypto series returned no BTC/ETH tickers; aborting market discovery")

        return pages

    async def _fetch_weather_markets(self, category: str, markets: List[Dict[str, object]], seen_tickers: set[str]) -> int:
        """Fetch weather-specific markets."""
        from common.kalshi_api import KalshiClientError

        try:
            series_list = await self._client.get_series(category=category)
        except (KalshiClientError, KeyError, TypeError, ValueError) as exc:
            raise KalshiMarketCatalogError(f"Failed to fetch Kalshi weather series for {category}") from exc

        pages = 0
        matched_series = 0
        for series in series_list:
            ticker = series.get("ticker") if isinstance(series, dict) else None
            if not ticker or not ticker.upper().startswith("KXHIGH"):
                continue

            matched_series += 1
            weather_params: BaseParams = {"category": category, "series_ticker": ticker}
            pages += await self._fetcher_client.fetch_markets(
                f"series {ticker}",
                markets,
                seen_tickers,
                base_params=weather_params,
            )

        if matched_series == 0:
            raise KalshiMarketCatalogError(f"Weather series for {category} returned no KXHIGH tickers; aborting market discovery")

        return pages
