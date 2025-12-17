"""Handle fills operations."""

from typing import Any, Dict, Optional

from .base import ClientOperationBase


class FillsOperations(ClientOperationBase):
    """Handle fills-related API operations."""

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
