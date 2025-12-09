"""REST request operations."""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

# Constants
HTTP_SUCCESS_MIN = 200  # Minimum HTTP status code for success
HTTP_CLIENT_ERROR_MIN = 400  # Minimum HTTP status code for client errors


class RESTRequestOperations:
    """Handles REST API request operations."""

    def __init__(
        self,
        service_name: str,
        base_url: str,
        session_manager,
        auth_handler,
        health_monitor,
    ):
        self.service_name = service_name
        self.base_url = base_url
        self.session_manager = session_manager
        self.auth_handler = auth_handler
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[aiohttp.ClientResponse]:
        """Make HTTP request."""
        session = self.session_manager.get_session()
        if not session:
            self.logger.warning("Cannot make request - session not connected")
            return None

        try:
            url = f"{self.base_url}{endpoint}"
            self.logger.debug(f"Making {method} request: {url}")

            if self.auth_handler and "headers" not in kwargs:
                kwargs["headers"] = self._get_auth_headers(method, endpoint)

            response = await session.request(method, url, **kwargs)

        except aiohttp.ClientError:
            self.logger.exception("HTTP request failed")
            if self.health_monitor:
                self.health_monitor.record_failure()
            return None
        except (asyncio.TimeoutError, OSError, RuntimeError):
            self.logger.exception("Unexpected error making request")
            if self.health_monitor:
                self.health_monitor.record_failure()
            return None
        else:
            self._record_response_health(response)
            return response

    def _get_auth_headers(self, method: str, endpoint: str) -> Optional[Dict[str, str]]:
        """Get authentication headers from handler."""
        try:
            return self.auth_handler(method, endpoint)
        except TypeError:
            return self.auth_handler()

    def _record_response_health(self, response: aiohttp.ClientResponse) -> None:
        """Record response health status to monitor."""
        if not self.health_monitor:
            return
        if HTTP_SUCCESS_MIN <= response.status < HTTP_CLIENT_ERROR_MIN:
            self.health_monitor.record_success()
        else:
            self.health_monitor.record_failure()

    async def make_json_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request and parse JSON response."""
        response = await self.make_request(method, endpoint, **kwargs)

        if response is None:
            return None
        status = response.status
        try:
            async with response:
                if response.content_type == "application/json":
                    json_data = await response.json()
                    self.logger.debug("Received JSON response")
                    return json_data
                else:
                    if self.health_monitor and status < HTTP_CLIENT_ERROR_MIN:
                        self.health_monitor.record_request_failure()
                    self.logger.warning("Expected JSON but got %s", response.content_type)
                    return None

        except (aiohttp.ContentTypeError, ValueError, RuntimeError, SyntaxError):
            self.logger.exception(f"Failed to parse JSON response: ")
            if self.health_monitor and status < HTTP_CLIENT_ERROR_MIN:
                self.health_monitor.record_failure()
            return None
