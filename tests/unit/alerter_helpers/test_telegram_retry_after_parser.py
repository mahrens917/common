"""Tests for telegram_retry_after_parser module."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from common.alerter_helpers.telegram_retry_after_parser import TelegramRetryAfterParser


class TestParseHeaderValue:
    """Tests for _parse_header_value method."""

    def test_valid_integer(self) -> None:
        """Test parsing valid integer."""
        result = TelegramRetryAfterParser._parse_header_value("30")
        assert result == 30

    def test_valid_float(self) -> None:
        """Test parsing valid float."""
        result = TelegramRetryAfterParser._parse_header_value("30.5")
        assert result == 30

    def test_zero_returns_one(self) -> None:
        """Test zero returns minimum of 1."""
        result = TelegramRetryAfterParser._parse_header_value("0")
        assert result == 1

    def test_negative_returns_one(self) -> None:
        """Test negative returns minimum of 1."""
        result = TelegramRetryAfterParser._parse_header_value("-5")
        assert result == 1

    def test_invalid_string(self) -> None:
        """Test invalid string returns None."""
        result = TelegramRetryAfterParser._parse_header_value("invalid")
        assert result is None


class TestFetchJsonPayload:
    """Tests for _fetch_json_payload method."""

    @pytest.mark.asyncio
    async def test_valid_json(self) -> None:
        """Test fetching valid JSON payload."""
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.json = AsyncMock(return_value={"parameters": {"retry_after": 30}})

        result = await TelegramRetryAfterParser._fetch_json_payload(response)

        assert result == {"parameters": {"retry_after": 30}}

    @pytest.mark.asyncio
    async def test_content_type_error(self) -> None:
        """Test handling ContentTypeError."""
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock()))

        result = await TelegramRetryAfterParser._fetch_json_payload(response)

        assert result is None

    @pytest.mark.asyncio
    async def test_value_error(self) -> None:
        """Test handling ValueError."""
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

        result = await TelegramRetryAfterParser._fetch_json_payload(response)

        assert result is None


class TestParseRetryFromPayload:
    """Tests for _parse_retry_from_payload method."""

    def test_valid_payload(self) -> None:
        """Test parsing valid payload."""
        payload = {"parameters": {"retry_after": 30}}

        result = TelegramRetryAfterParser._parse_retry_from_payload(payload)

        assert result == 30

    def test_float_retry_after(self) -> None:
        """Test parsing float retry_after."""
        payload = {"parameters": {"retry_after": 30.7}}

        result = TelegramRetryAfterParser._parse_retry_from_payload(payload)

        assert result == 30

    def test_missing_parameters(self) -> None:
        """Test missing parameters key."""
        payload = {}

        result = TelegramRetryAfterParser._parse_retry_from_payload(payload)

        assert result is None

    def test_parameters_not_dict(self) -> None:
        """Test parameters is not a dict."""
        payload = {"parameters": "invalid"}

        result = TelegramRetryAfterParser._parse_retry_from_payload(payload)

        assert result is None

    def test_missing_retry_after(self) -> None:
        """Test missing retry_after in parameters."""
        payload = {"parameters": {"other": "value"}}

        result = TelegramRetryAfterParser._parse_retry_from_payload(payload)

        assert result is None

    def test_invalid_retry_after_type(self) -> None:
        """Test invalid retry_after type."""
        payload = {"parameters": {"retry_after": "invalid"}}

        result = TelegramRetryAfterParser._parse_retry_from_payload(payload)

        assert result is None

    def test_minimum_retry_after(self) -> None:
        """Test minimum retry_after is 1."""
        payload = {"parameters": {"retry_after": 0}}

        result = TelegramRetryAfterParser._parse_retry_from_payload(payload)

        assert result == 1


class TestExtractRetryAfterSeconds:
    """Tests for extract_retry_after_seconds method."""

    @pytest.mark.asyncio
    async def test_from_header(self) -> None:
        """Test extracting from Retry-After header."""
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.headers = {"Retry-After": "60"}

        result = await TelegramRetryAfterParser.extract_retry_after_seconds(response)

        assert result == 60

    @pytest.mark.asyncio
    async def test_from_payload(self) -> None:
        """Test extracting from JSON payload."""
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.headers = {}
        response.json = AsyncMock(return_value={"parameters": {"retry_after": 45}})

        result = await TelegramRetryAfterParser.extract_retry_after_seconds(response)

        assert result == 45

    @pytest.mark.asyncio
    async def test_no_retry_after(self) -> None:
        """Test when no retry-after available."""
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.headers = {}
        response.json = AsyncMock(return_value={})

        result = await TelegramRetryAfterParser.extract_retry_after_seconds(response)

        assert result is None

    @pytest.mark.asyncio
    async def test_header_preferred_over_payload(self) -> None:
        """Test header is preferred over payload."""
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.headers = {"Retry-After": "30"}
        response.json = AsyncMock(return_value={"parameters": {"retry_after": 60}})

        result = await TelegramRetryAfterParser.extract_retry_after_seconds(response)

        assert result == 30
