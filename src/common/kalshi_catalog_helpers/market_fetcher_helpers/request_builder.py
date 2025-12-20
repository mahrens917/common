"""Request parameter building for market fetching."""

from typing import Dict, Optional


class RequestBuilder:
    """Builds request parameters for market fetching."""

    @staticmethod
    def build_params(
        base_params: Optional[Dict[str, Optional[str]]],
        cursor: Optional[str],
        market_status: str,
    ) -> Dict[str, Optional[str]]:
        """Build request parameters with status and optional cursor."""
        params: Dict[str, Optional[str]] = dict(base_params) if base_params else {}
        params["status"] = market_status
        if cursor:
            params["cursor"] = cursor
        return params
