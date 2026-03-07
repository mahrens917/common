"""Initialize KalshiClient components and handle series operations."""

from typing import Any, Dict, List, Optional

from common.api_response_validators import validate_series_response

from ..authentication import AuthenticationHelper
from ..order_operations import OrderOperations
from ..portfolio_operations import PortfolioOperations
from ..request_builder import RequestBuilder
from ..session_manager import SessionManager
from .errors import KalshiClientError


class ComponentInitializer:
    """Initialize all helper components for KalshiClient."""

    def __init__(self, config):
        """Initialize with config."""
        self.config = config

    def initialize(self, access_key: str, private_key):
        """Initialize all helper components."""
        session_manager = SessionManager(self.config)
        auth_helper = AuthenticationHelper(access_key, private_key)
        request_builder = RequestBuilder(
            self.config.base_url,
            session_manager,
            auth_helper,
            self.config.network_max_retries,
            self.config.network_backoff_base_seconds,
            self.config.network_backoff_max_seconds,
        )
        portfolio_ops = PortfolioOperations(request_builder)
        order_ops = OrderOperations(request_builder)

        return {
            "session_manager": session_manager,
            "auth_helper": auth_helper,
            "request_builder": request_builder,
            "portfolio_ops": portfolio_ops,
            "order_ops": order_ops,
        }


class SeriesOperations:
    """Handle series-related API operations."""

    def __init__(self, client: Any) -> None:
        self.client = client

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
