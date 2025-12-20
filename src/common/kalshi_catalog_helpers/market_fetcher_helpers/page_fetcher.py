"""Page fetching logic for market data."""

from typing import Any, Dict


class PageFetcher:
    """Fetches individual pages of market data."""

    def __init__(self, client):
        """Initialize with API client."""
        self._client = client

    async def fetch_page(self, params: Dict[str, Any]) -> Dict[str, object]:
        """Fetch a single page of markets from the API."""
        from common.kalshi_api import KalshiClientError
        from ..market_fetcher import KalshiMarketCatalogError

        try:
            payload = await self._client.api_request(
                method="GET",
                path="/trade-api/v2/markets",
                params=params,
                operation_name="fetch_markets",
            )
        except KalshiClientError as exc:
            raise KalshiMarketCatalogError(f"Kalshi market request failed") from exc

        if not isinstance(payload, dict):
            raise KalshiMarketCatalogError("Kalshi markets payload was not a JSON object")
        return payload
