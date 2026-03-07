"""Handle fills and market status operations."""

from typing import Any, Dict, Optional

from common.api_response_validators import validate_exchange_status_response


class FillsOperations:
    """Handle fills-related API operations."""

    def __init__(self, client: Any) -> None:
        self.client = client

    async def get_all_fills(
        self,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        ticker: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all fills with optional filters."""
        params = self._build_params(min_ts, max_ts, ticker, cursor)
        return await self.client.api_request(
            method="GET",
            path="/trade-api/v2/portfolio/fills",
            params=params,
            operation_name="get_all_fills",
        )

    @staticmethod
    def _build_params(
        min_ts: Optional[int],
        max_ts: Optional[int],
        ticker: Optional[str],
        cursor: Optional[str],
    ) -> Dict[str, Any]:
        """Build parameters for fills request."""
        params: Dict[str, Any] = {}
        if min_ts is not None:
            params["min_ts"] = int(min_ts)
        if max_ts is not None:
            params["max_ts"] = int(max_ts)
        if ticker:
            params["ticker"] = ticker
        if cursor:
            params["cursor"] = cursor
        return params


class MarketStatusOperations:
    """Handle market status-related API operations."""

    def __init__(self, client: Any) -> None:
        self.client = client

    async def get_exchange_status(self) -> Dict[str, bool]:
        """Get exchange status."""
        payload = await self.client.api_request(
            method="GET",
            path="/trade-api/v2/exchange/status",
            params={},
            operation_name="get_exchange_status",
        )
        return validate_exchange_status_response(payload)

    async def is_market_open(self) -> bool:
        """Check if market is open."""
        status = await self.get_exchange_status()
        return status["exchange_active"] and status["trading_active"]
