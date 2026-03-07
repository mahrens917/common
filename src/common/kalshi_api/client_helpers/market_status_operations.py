"""Handle market status operations."""

from typing import Any, Dict

from common.api_response_validators import validate_exchange_status_response


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
