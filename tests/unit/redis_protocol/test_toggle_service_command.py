"""Tests for toggle_service_command module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.toggle_service_command import (
    DISABLED_SERVICES_KEY,
    RESULT_TTL_SECONDS,
    TOGGLE_SERVICE_COMMAND_KEY,
    TOGGLE_SERVICE_RESULT_KEY,
    ToggleServiceResult,
    clear_toggle_service_command,
    clear_toggle_service_result,
    get_toggle_service_command,
    get_toggle_service_result,
    is_service_disabled,
    mark_service_disabled,
    mark_service_enabled,
    request_toggle_service,
    write_toggle_service_result,
)


class TestConstants:
    """Tests for module constants."""

    def test_command_key_value(self):
        assert TOGGLE_SERVICE_COMMAND_KEY == "config:command:toggle_service"

    def test_result_key_value(self):
        assert TOGGLE_SERVICE_RESULT_KEY == "config:command:toggle_service:result"

    def test_result_ttl_seconds(self):
        assert RESULT_TTL_SECONDS == 30

    def test_disabled_services_key(self):
        assert DISABLED_SERVICES_KEY == "config:disabled_services"


class TestToggleServiceResult:
    """Tests for ToggleServiceResult dataclass."""

    def test_create_result(self):
        result = ToggleServiceResult(
            service_name="kalshi",
            action="stop",
            success=True,
            timestamp="2024-01-15T12:00:00+00:00",
        )

        assert result.service_name == "kalshi"
        assert result.action == "stop"
        assert result.success is True
        assert result.timestamp == "2024-01-15T12:00:00+00:00"


class TestRequestToggleService:
    """Tests for request_toggle_service function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_sets_command_to_redis(self, mock_redis):
        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value.isoformat.return_value = "2024-01-15T12:00:00+00:00"

            await request_toggle_service(mock_redis, "kalshi", "stop")

            expected_payload = json.dumps(
                {
                    "service_name": "kalshi",
                    "action": "stop",
                    "timestamp": "2024-01-15T12:00:00+00:00",
                }
            )
            mock_redis.set.assert_called_once_with(TOGGLE_SERVICE_COMMAND_KEY, expected_payload)


class TestGetToggleServiceCommand:
    """Tests for get_toggle_service_command function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_none_when_no_command(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_toggle_service_command(mock_redis)

        assert result is None
        mock_redis.get.assert_called_once_with(TOGGLE_SERVICE_COMMAND_KEY)

    @pytest.mark.asyncio
    async def test_returns_tuple_from_bytes(self, mock_redis):
        payload = json.dumps(
            {
                "service_name": "kalshi",
                "action": "stop",
                "timestamp": "2024-01-15T12:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=payload.encode("utf-8"))

        result = await get_toggle_service_command(mock_redis)

        assert result == ("kalshi", "stop", "2024-01-15T12:00:00+00:00")

    @pytest.mark.asyncio
    async def test_returns_tuple_from_string(self, mock_redis):
        payload = json.dumps(
            {
                "service_name": "deribit",
                "action": "start",
                "timestamp": "2024-01-15T14:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=payload)

        result = await get_toggle_service_command(mock_redis)

        assert result == ("deribit", "start", "2024-01-15T14:00:00+00:00")


class TestClearToggleServiceCommand:
    """Tests for clear_toggle_service_command function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_deletes_command_key(self, mock_redis):
        await clear_toggle_service_command(mock_redis)

        mock_redis.delete.assert_called_once_with(TOGGLE_SERVICE_COMMAND_KEY)


class TestWriteToggleServiceResult:
    """Tests for write_toggle_service_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_writes_result_to_redis(self, mock_redis):
        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value.isoformat.return_value = "2024-01-15T12:00:00+00:00"

            await write_toggle_service_result(mock_redis, service_name="kalshi", action="stop", success=True)

            expected_data = json.dumps(
                {
                    "service_name": "kalshi",
                    "action": "stop",
                    "success": True,
                    "timestamp": "2024-01-15T12:00:00+00:00",
                }
            )
            mock_redis.set.assert_called_once_with(TOGGLE_SERVICE_RESULT_KEY, expected_data, ex=RESULT_TTL_SECONDS)


class TestGetToggleServiceResult:
    """Tests for get_toggle_service_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_none_when_no_result(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_toggle_service_result(mock_redis)

        assert result is None
        mock_redis.get.assert_called_once_with(TOGGLE_SERVICE_RESULT_KEY)

    @pytest.mark.asyncio
    async def test_returns_result_from_bytes(self, mock_redis):
        data = json.dumps(
            {
                "service_name": "kalshi",
                "action": "stop",
                "success": True,
                "timestamp": "2024-01-15T12:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=data.encode("utf-8"))

        result = await get_toggle_service_result(mock_redis)

        assert result is not None
        assert result.service_name == "kalshi"
        assert result.action == "stop"
        assert result.success is True
        assert result.timestamp == "2024-01-15T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_returns_result_from_string(self, mock_redis):
        data = json.dumps(
            {
                "service_name": "deribit",
                "action": "start",
                "success": False,
                "timestamp": "2024-01-15T14:00:00+00:00",
            }
        )
        mock_redis.get = AsyncMock(return_value=data)

        result = await get_toggle_service_result(mock_redis)

        assert result is not None
        assert result.service_name == "deribit"
        assert result.action == "start"
        assert result.success is False
        assert result.timestamp == "2024-01-15T14:00:00+00:00"


class TestClearToggleServiceResult:
    """Tests for clear_toggle_service_result function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_deletes_result_key(self, mock_redis):
        await clear_toggle_service_result(mock_redis)

        mock_redis.delete.assert_called_once_with(TOGGLE_SERVICE_RESULT_KEY)


class TestMarkServiceDisabled:
    """Tests for mark_service_disabled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.sadd = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_adds_service_to_disabled_set(self, mock_redis):
        await mark_service_disabled(mock_redis, "kalshi")

        mock_redis.sadd.assert_called_once_with(DISABLED_SERVICES_KEY, "kalshi")


class TestMarkServiceEnabled:
    """Tests for mark_service_enabled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.srem = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_removes_service_from_disabled_set(self, mock_redis):
        await mark_service_enabled(mock_redis, "kalshi")

        mock_redis.srem.assert_called_once_with(DISABLED_SERVICES_KEY, "kalshi")


class TestIsServiceDisabled:
    """Tests for is_service_disabled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.sismember = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_true_when_disabled(self, mock_redis):
        mock_redis.sismember = AsyncMock(return_value=1)

        result = await is_service_disabled(mock_redis, "kalshi")

        assert result is True
        mock_redis.sismember.assert_called_once_with(DISABLED_SERVICES_KEY, "kalshi")

    @pytest.mark.asyncio
    async def test_returns_false_when_not_disabled(self, mock_redis):
        mock_redis.sismember = AsyncMock(return_value=0)

        result = await is_service_disabled(mock_redis, "kalshi")

        assert result is False
