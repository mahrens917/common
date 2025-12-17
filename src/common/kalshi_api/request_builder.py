"""Request building and execution for Kalshi API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from .client_helpers.errors import KalshiClientError
from .request_executor import RequestExecutor

if TYPE_CHECKING:
    from .authentication import AuthenticationHelper
    from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class RequestBuilder:
    """Builds and executes Kalshi API requests - slim coordinator."""

    def __init__(
        self,
        base_url: str,
        session_manager: SessionManager,
        auth_helper: AuthenticationHelper,
        max_retries: int,
        backoff_base: float,
        backoff_max: float,
    ) -> None:
        self._base_url = base_url
        self._executor = RequestExecutor(session_manager, auth_helper, max_retries, backoff_base, backoff_max)

    def build_request_context(
        self,
        *,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]],
        json_payload: Optional[Dict[str, Any]],
        operation_name: Optional[str],
    ) -> Tuple[str, str, Dict[str, Any], str]:
        """Build request context from parameters."""
        if not path.startswith("/"):
            raise KalshiClientError("Path must begin with '/' for Kalshi requests")

        method_upper = method.upper()
        url = f"{self._base_url}{path}"
        op = operation_name if operation_name else path

        request_kwargs: Dict[str, Any] = {}
        if params:
            request_kwargs["params"] = params
        if json_payload is not None:
            request_kwargs["json"] = json_payload

        return method_upper, url, request_kwargs, op

    async def execute_request(
        self,
        method_upper: str,
        url: str,
        request_kwargs: Dict[str, Any],
        path: str,
        operation_name: str,
    ) -> Dict[str, Any]:
        """Execute HTTP request with retries."""
        return await self._executor.execute_request(method_upper, url, request_kwargs, path, operation_name)
