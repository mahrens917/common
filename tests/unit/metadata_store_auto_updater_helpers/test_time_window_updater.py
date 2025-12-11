import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.metadata_store_auto_updater_helpers.time_window_updater import TimeWindowUpdater
from common.metadata_store_auto_updater_helpers.time_window_updater_helpers.hash_validator import (
    HashValidator,
)
from common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater import (
    ServiceUpdater,
    _calculate_window_counts,
    _persist_counts,
)


class TestTimeWindowUpdater:
    @pytest.fixture
    def metadata_store(self):
        store = AsyncMock()
        store.get_all_services.return_value = ["service1", "service2"]
        return store

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def updater(self, metadata_store, mock_redis):
        return TimeWindowUpdater(metadata_store, mock_redis)

    @pytest.mark.asyncio
    async def test_run_updates_windows(self, updater):
        # Mock sleep to trigger once then shutdown
        updater._service_updater.update_service_time_windows = AsyncMock()

        async def side_effect(*args):
            updater.request_shutdown()

        with patch("asyncio.sleep", side_effect=side_effect):
            await updater.run()

        updater._service_updater.update_service_time_windows.assert_any_call("service1")
        updater._service_updater.update_service_time_windows.assert_any_call("service2")

    @pytest.mark.asyncio
    async def test_run_handles_error(self, updater):
        updater._service_updater.update_service_time_windows = AsyncMock(side_effect=Exception("Update error"))

        async def side_effect(*args):
            updater.request_shutdown()

        with (
            patch("asyncio.sleep", side_effect=side_effect),
            patch("common.metadata_store_auto_updater_helpers.time_window_updater.logger") as mock_logger,
        ):
            await updater.run()
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_run_cancelled(self, updater):
        with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await updater.run()


class TestServiceUpdater:
    @pytest.fixture
    def metadata_store(self):
        return AsyncMock()

    @pytest.fixture
    def mock_redis(self):
        client = AsyncMock()
        client.hgetall.return_value = {}
        return client

    @pytest.fixture
    def updater(self, metadata_store, mock_redis):
        return ServiceUpdater(metadata_store, mock_redis)

    @pytest.mark.asyncio
    async def test_update_service_time_windows_success(self, updater, mock_redis, metadata_store):
        mock_redis.hgetall.return_value = {
            b"2023-01-01 12:00:00": b"5",
            "2023-01-01 12:30:00": "10",
        }

        with (
            patch(
                "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_hash",
                return_value=True,
            ),
            patch("common.time_utils.get_current_utc") as mock_time,
            patch(
                "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._calculate_window_counts"
            ) as mock_calc,
            patch("common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._persist_counts") as mock_persist,
        ):

            mock_time.return_value = datetime(2023, 1, 1, 13, 0, 0)
            mock_calc.return_value = {"hour": 15, "sixty_five_minutes": 15, "sixty_seconds": 0}

            await updater.update_service_time_windows("test_service")

            mock_redis.hgetall.assert_awaited_once()
            mock_persist.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_service_time_windows_unsupported_hash(self, updater):
        with patch(
            "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_hash",
            return_value=False,
        ):
            await updater.update_service_time_windows("test_service")
            updater.redis_client.hgetall.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_service_time_windows_no_client(self, updater):
        updater.redis_client = None
        with patch(
            "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_hash",
            return_value=True,
        ):
            await updater.update_service_time_windows("test_service")
            # Should return early

    @pytest.mark.asyncio
    async def test_calculate_window_counts(self):
        windows = {
            "hour": "2023-01-01 12:00:00",
            "sixty_five_minutes": "2023-01-01 11:55:00",
            "sixty_seconds": "2023-01-01 12:59:00",
        }
        hash_data = {
            "2023-01-01 12:30:00": "10",  # In hour, in 65m
            "2023-01-01 11:50:00": "5",  # Out of all
            "2023-01-01 12:59:30": b"2",  # In all
            "1999-01-01 00:00:00": "1",  # Out of all
        }

        counts = _calculate_window_counts(hash_data, windows)
        assert counts["hour"] == 10 + 2
        assert counts["sixty_five_minutes"] == 10 + 2
        assert counts["sixty_seconds"] == 2

    @pytest.mark.asyncio
    async def test_persist_counts_weather(self, metadata_store):
        counts = {"hour": 1, "sixty_five_minutes": 2, "sixty_seconds": 3}
        await _persist_counts(metadata_store, "asos", counts)
        metadata_store.update_weather_time_window_counts.assert_awaited_with("asos", 1, 3, 2)

    @pytest.mark.asyncio
    async def test_persist_counts_generic(self, metadata_store):
        counts = {"hour": 1, "sixty_five_minutes": 2, "sixty_seconds": 3}
        await _persist_counts(metadata_store, "generic", counts)
        metadata_store.update_time_window_counts.assert_awaited_with("generic", 1, 3)


class TestHashValidator:
    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_hash(self, mock_redis):
        mock_redis.type.return_value = "hash"
        assert await HashValidator.ensure_hash_history_key(mock_redis, "key") is True

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_none(self, mock_redis):
        mock_redis.type.return_value = b"none"
        assert await HashValidator.ensure_hash_history_key(mock_redis, "key") is True

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_invalid(self, mock_redis):
        mock_redis.type.return_value = "string"
        assert await HashValidator.ensure_hash_history_key(mock_redis, "key") is False

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_error(self, mock_redis):
        mock_redis.type.side_effect = Exception("Redis error")
        assert await HashValidator.ensure_hash_history_key(mock_redis, "key") is False

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_no_client(self):
        assert await HashValidator.ensure_hash_history_key(None, "key") is False
