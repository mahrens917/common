"""Parse retry-after hints from Telegram 429 responses."""

import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class TelegramRetryAfterParser:
    """Parses retry-after hints from Telegram API 429 responses."""

    @staticmethod
    def _parse_header_value(header_value: str) -> Optional[int]:
        """Parse retry-after from header value."""
        try:
            return max(1, int(float(header_value)))
        except ValueError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.debug("Unable to parse Retry-After header value: %s", header_value)
            return None

    @staticmethod
    async def _fetch_json_payload(response: aiohttp.ClientResponse) -> Optional[dict]:
        """Fetch JSON payload from response."""
        try:
            return await response.json()
        except aiohttp.ContentTypeError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.warning("Expected data validation or parsing failure")
            return None
        except (  # policy_guard: allow-silent-handler
            aiohttp.ClientError,
            ValueError,
        ) as exc:
            logger.debug("Failed to parse Telegram 429 payload: %s", exc)
            return None

    @staticmethod
    def _parse_retry_from_payload(payload: dict) -> Optional[int]:
        """Parse retry-after from JSON payload parameters."""
        parameters = payload.get("parameters")
        if not isinstance(parameters, dict):
            return None

        retry_after = parameters.get("retry_after")
        if retry_after is None:
            return None

        try:
            retry_seconds = float(retry_after)
        except (  # policy_guard: allow-silent-handler
            TypeError,
            ValueError,
        ):
            logger.debug("Invalid retry_after value in Telegram payload: %s", retry_after)
            return None
        return max(1, int(retry_seconds))

    @classmethod
    async def extract_retry_after_seconds(
        cls,
        response: aiohttp.ClientResponse,
    ) -> Optional[int]:
        """
        Extract retry-after seconds from Telegram backoff hints.

        Args:
            response: HTTP response with 429 status

        Returns:
            Retry-after seconds if available
        """
        header_value = response.headers.get("Retry-After")
        if header_value:
            result = cls._parse_header_value(header_value)
            if result is not None:
                return result

        payload = await cls._fetch_json_payload(response)
        if payload:
            return cls._parse_retry_from_payload(payload)
        return None
