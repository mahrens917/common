"""Tests for restart_service_command module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.restart_service_command import (
    RESTART_SERVICE_COMMAND_KEY,
    RESTART_SERVICE_RESULT_KEY,
    RESULT_TTL_SECONDS,
    RestartServiceResult,
    clear_restart_service_command,
    clear_restart_service_result,
    get_restart_service_command,
    get_restart_service_result,
    request_restart_service,
    write_restart_service_result,
)


class TestConstants:
    """Tests for module constants."""

    def test_command_key_value(self):
        assert RESTART_SERVICE_COMMAND_KEY == "config:command:restart_service"

    def test_result_key_value(self):
        assert RESTART_SERVICE_RESULT_KEY == "config:command:restart_service:result"

    def test_result_ttl_seconds(self):
        assert RESULT_TTL_SECONDS == 30


class TestRestartServiceResult:
    """Tests for RestartServiceResult dataclass."""

    def test_create_result(self):
        result = RestartServiceResult(
            service_name="kalshi",
            success=True,
            timestamp="2024-01-15T12:00:00+00:00",
        )

        assert result.service_name == "kalshi"
        assert result.success is True
        assert result.timestamp == "2024-01-15T12:00:00+00:00"


class TestRequestRestartService:
    """Tests for request_restart_service function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_sets_command_to_redis(self, mock_redis):
        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value.isoformat.return_value = "2024-01-15T12:00:00+00:00"

            await request_restart_service(mock_redis, "kalshi")

            expected_payload = json.dumps({"service_name": "kalshi", "timestamp": "2024-01-15T12:00:00+00:00"})
            mock_redis.set.assert_called_once_with(RESTART_SERVICE_COMMAND_KEY, expected_payload)


class TestGetRestartServiceCommand:
    """Tests for get_restart_service_command function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_none_when_no_command(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_restart_service_command(mock_redis)

        assert result is None
        mock_redis.get.assert_called_once_with(RESTART_SERVICE_COMMAND_KEY)

    @pytest.mark.asyncio
    async def test_returns_tuple_from_bytes(self, mock_redis):
        payload = json.dumps({"service_name": "kalshi", "timestamp": "2024-01-15T12:00:00+00:00"})
        mock_redis.get = AsyncMock(return_value=payload.encode("utf-8"))

        result = await get_restart_service_command(mock_redis)

        assert result == ("kalshi", "2024-01-15T12:00:00+00:00")

    @pytest.mark.asyncio
    async def test_returns_tuple_from_string(self, mock_redis):
        payload = json.dumps({"service_name": "deribit", "timestamp": "2024-01-15T14:00:00+00:00"})
        mock_redis.get = AsyncMock(return_value=payload)

        result = await get_restart_service_command(mock_redis)

        assert result == ("deribit", "2024-01-15T14:00:00+00:00")


class TestClearRestartServiceCommand:
    """Tests for clear_restart_service_command function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_deletes_command_key(self, mock_redis):
        await clear_restart_service_command(mock_redis)

        mock_redis.delete.assert_called_once_with(RESTART_SERVICE_COMMAND_KEY)


class TestWriteRestartServiceResult:
    """Tests for write_restart_service_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_writes_result_to_redis(self, mock_redis):
        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value.isoformat.return_value = "2024-01-15T12:00:00+00:00"

            await write_restart_service_result(mock_redis, service_name="kalshi", success=True)

            expected_data = json.dumps(
                {
                    "service_name": "kalshi",
                    "success": True,
                    "timestamp": "2024-01-15T12:00:00+00:00",
                }
            )
            mock_redis.set.assert_called_once_with(RESTART_SERVICE_RESULT_KEY, expected_data, ex=RESULT_TTL_SECONDS)


class TestGetRestartServiceResult:
    """Tests for get_restart_service_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_none_when_no_result(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_restart_service_result(mock_redis)

        assert result is None
        mock_redis.get.assert_called_once_with(RESTART_SERVICE_RESULT_KEY)

    @pytest.mark.asyncio
    async def test_returns_result_from_bytes(self, mock_redis):
        data = json.dumps(
            {
                "service_name": "kalshi",
                "success": True,
                "timestamp": "2024-01-15T12:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=data.encode("utf-8"))

        result = await get_restart_service_result(mock_redis)

        assert result is not None
        assert result.service_name == "kalshi"
        assert result.success is True
        assert result.timestamp == "2024-01-15T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_returns_result_from_string(self, mock_redis):
        data = json.dumps(
            {
                "service_name": "deribit",
                "success": False,
                "timestamp": "2024-01-15T14:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=data)

        result = await get_restart_service_result(mock_redis)

        assert result is not None
        assert result.service_name == "deribit"
        assert result.success is False
        assert result.timestamp == "2024-01-15T14:00:00+00:00"


class TestClearRestartServiceResult:
    """Tests for clear_restart_service_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_deletes_result_key(self, mock_redis):
        await clear_restart_service_result(mock_redis)

        mock_redis.delete.assert_called_once_with(RESTART_SERVICE_RESULT_KEY)
