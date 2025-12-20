"""Page payload validation."""

from typing import Any, Dict, List


class PageValidator:
    """Validates and extracts data from page payloads."""

    @staticmethod
    def extract_markets(payload: Dict[str, object]) -> List[Any]:
        """Extract and validate markets list from page payload."""
        from ..market_fetcher import KalshiMarketCatalogError

        page_markets = payload.get("markets")
        if not isinstance(page_markets, list):
            raise KalshiMarketCatalogError("Kalshi markets payload missing 'markets'")
        return page_markets
