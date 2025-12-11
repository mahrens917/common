"""Tests for key scanner module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.persistence_manager_helpers.key_scanner import KeyScanner


class TestKeyScanner:
    """Tests for KeyScanner class."""

    def test_can_instantiate(self) -> None:
        """Can create KeyScanner instance."""
        scanner = KeyScanner()

        assert scanner is not None


class TestGetConfigInfo:
    """Tests for get_config_info method."""

    @pytest.mark.asyncio
    async def test_returns_config_from_redis(self) -> None:
        """Returns config from Redis config_get."""
        scanner = KeyScanner()
        redis = AsyncMock()
        redis.config_get = AsyncMock(return_value={"maxmemory": "100mb", "timeout": "0"})

        result = await scanner.get_config_info(redis)

        assert result == {"maxmemory": "100mb", "timeout": "0"}
        redis.config_get.assert_called_once_with("*")

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_error(self) -> None:
        """Returns empty dict on Redis error."""
        from redis.exceptions import RedisError

        scanner = KeyScanner()
        redis = AsyncMock()
        redis.config_get = AsyncMock(side_effect=RedisError("Connection failed"))

        with patch("common.redis_protocol.persistence_manager_helpers.key_scanner.logger"):
            result = await scanner.get_config_info(redis)

        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_connection_error(self) -> None:
        """Returns empty dict on connection error."""
        scanner = KeyScanner()
        redis = AsyncMock()
        redis.config_get = AsyncMock(side_effect=ConnectionError("Connection failed"))

        with patch("common.redis_protocol.persistence_manager_helpers.key_scanner.logger"):
            result = await scanner.get_config_info(redis)

        assert result == {}


class TestGetPersistenceInfo:
    """Tests for get_persistence_info method."""

    @pytest.mark.asyncio
    async def test_returns_persistence_info(self) -> None:
        """Returns persistence info from Redis."""
        scanner = KeyScanner()
        redis = AsyncMock()
        redis.info = AsyncMock(return_value={"aof_enabled": "1", "rdb_last_save_time": "1234567890"})

        result = await scanner.get_persistence_info(redis)

        assert result == {"aof_enabled": "1", "rdb_last_save_time": "1234567890"}
        redis.info.assert_called_once_with("persistence")

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_error(self) -> None:
        """Returns empty dict on Redis error."""
        from redis.exceptions import RedisError

        scanner = KeyScanner()
        redis = AsyncMock()
        redis.info = AsyncMock(side_effect=RedisError("Connection failed"))

        with patch("common.redis_protocol.persistence_manager_helpers.key_scanner.logger"):
            result = await scanner.get_persistence_info(redis)

        assert result == {}


class TestExtractConfigValue:
    """Tests for extract_config_value method."""

    def test_returns_value_when_present(self) -> None:
        """Returns value when key present."""
        scanner = KeyScanner()
        config_info = {"maxmemory": "100mb"}

        result = scanner.extract_config_value(config_info, "maxmemory")

        assert result == "100mb"

    def test_returns_default_when_missing(self) -> None:
        """Returns default when key missing."""
        scanner = KeyScanner()
        config_info = {}

        result = scanner.extract_config_value(config_info, "maxmemory", "50mb")

        assert result == "50mb"

    def test_returns_none_default_when_missing(self) -> None:
        """Returns None when key missing and no default."""
        scanner = KeyScanner()
        config_info = {}

        result = scanner.extract_config_value(config_info, "maxmemory")

        assert result is None


class TestExtractInfoValue:
    """Tests for extract_info_value method."""

    def test_returns_value_when_present(self) -> None:
        """Returns value when key present."""
        scanner = KeyScanner()
        info = {"aof_enabled": "1"}

        result = scanner.extract_info_value(info, "aof_enabled")

        assert result == "1"

    def test_returns_default_when_missing(self) -> None:
        """Returns default when key missing."""
        scanner = KeyScanner()
        info = {}

        result = scanner.extract_info_value(info, "aof_enabled", "0")

        assert result == "0"

    def test_returns_none_default_when_missing(self) -> None:
        """Returns None when key missing and no default."""
        scanner = KeyScanner()
        info = {}

        result = scanner.extract_info_value(info, "aof_enabled")

        assert result is None
