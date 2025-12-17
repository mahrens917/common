"""Handle series operations."""

from typing import Any, Dict, List, Optional

from common.api_response_validators import validate_series_response

from .base import ClientOperationBase
from .errors import KalshiClientError


class SeriesOperations(ClientOperationBase):
    """Handle series-related API operations."""

    async def get_series(self, *, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get series information with optional category filter."""
        params = self._build_params(category)
        if category is None:
            category_label = "all"
        else:
            category_label = category.lower()
        payload = await self.client.api_request(
            method="GET",
            path="/trade-api/v2/series",
            params=params,
            operation_name=f"get_series_{category_label}",
        )
        try:
            return validate_series_response(payload)
        except ValueError as exc:
            raise KalshiClientError("Kalshi series response invalid") from exc

    @staticmethod
    def _build_params(category: Optional[str]) -> Dict[str, Any]:
        """Build parameters for series request."""
        params: Dict[str, Any] = {}
        if category:
            params["category"] = category
        return params
