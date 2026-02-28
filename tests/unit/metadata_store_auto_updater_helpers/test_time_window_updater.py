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
    _coerce_int_from_member,
    _count_entries_per_window,
    _ensure_supported_sorted_set,
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
        client.zrangebyscore.return_value = []
        return client

    @pytest.fixture
    def updater(self, metadata_store, mock_redis):
        return ServiceUpdater(metadata_store, mock_redis)

    @pytest.mark.asyncio
    async def test_update_service_time_windows_success(self, updater, mock_redis, metadata_store):
        mock_redis.zrangebyscore.return_value = [
            (b"1672574400|5", 1672574400.0),
            ("1672576200|10", 1672576200.0),
        ]

        with (
            patch(
                "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_sorted_set",
                new_callable=AsyncMock,
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

            mock_redis.zrangebyscore.assert_awaited_once()
            mock_persist.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_service_time_windows_unsupported_hash(self, updater):
        with patch(
            "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_sorted_set",
            new_callable=AsyncMock,
            return_value=False,
        ):
            await updater.update_service_time_windows("test_service")
            updater.redis_client.zrangebyscore.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_service_time_windows_no_client(self, updater):
        updater.redis_client = None
        with patch(
            "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_sorted_set",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await updater.update_service_time_windows("test_service")
            # Should return early

    @pytest.mark.asyncio
    async def test_calculate_window_counts(self):
        cutoffs = {
            "hour": 1672574400.0,
            "sixty_five_minutes": 1672574100.0,
            "sixty_seconds": 1672577940.0,
        }
        entries = [
            ("1672576200|10", 1672576200.0),  # score >= hour cutoff -> hour, 65m
            (b"1672577970|2", 1672577970.0),  # score >= all cutoffs -> hour, 65m, 60s
            ("1672574200|5", 1672574200.0),  # score < hour cutoff -> 65m only
        ]

        counts = _calculate_window_counts(entries, cutoffs)
        assert counts["hour"] == 10 + 2
        assert counts["sixty_five_minutes"] == 10 + 2 + 5
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
    async def test_ensure_sorted_set_history_key_zset(self, mock_redis):
        mock_redis.type.return_value = "zset"
        assert await HashValidator.ensure_sorted_set_history_key(mock_redis, "key") is True

    @pytest.mark.asyncio
    async def test_ensure_sorted_set_history_key_none(self, mock_redis):
        mock_redis.type.return_value = b"none"
        assert await HashValidator.ensure_sorted_set_history_key(mock_redis, "key") is True

    @pytest.mark.asyncio
    async def test_ensure_sorted_set_history_key_invalid(self, mock_redis):
        mock_redis.type.return_value = "string"
        assert await HashValidator.ensure_sorted_set_history_key(mock_redis, "key") is False

    @pytest.mark.asyncio
    async def test_ensure_sorted_set_history_key_error(self, mock_redis):
        mock_redis.type.side_effect = Exception("Redis error")
        assert await HashValidator.ensure_sorted_set_history_key(mock_redis, "key") is False

    @pytest.mark.asyncio
    async def test_ensure_sorted_set_history_key_no_client(self):
        assert await HashValidator.ensure_sorted_set_history_key(None, "key") is False


class TestEnsureSupportedSortedSet:
    @pytest.mark.asyncio
    async def test_returns_true_for_valid_sorted_set(self):
        mock_redis = AsyncMock()
        mock_redis.type.return_value = "zset"
        result = await _ensure_supported_sorted_set(mock_redis, "history:svc", "svc")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_and_warns_for_invalid_type(self):
        mock_redis = AsyncMock()
        mock_redis.type.return_value = "string"
        with patch("common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater.logger") as mock_log:
            result = await _ensure_supported_sorted_set(mock_redis, "history:svc", "svc")
        assert result is False
        mock_log.warning.assert_called_once()


class TestCountEntriesPerWindow:
    def test_counts_all_entries_in_windows(self):
        cutoffs = {"hour": 1000.0, "sixty_five_minutes": 900.0, "sixty_seconds": 1100.0}
        entries = [
            (b"member1", 1050.0),  # >= hour, >= 65m, < 60s
            (b"member2", 1150.0),  # >= hour, >= 65m, >= 60s
            (b"member3", 950.0),  # < hour, >= 65m, < 60s
        ]
        counts = _count_entries_per_window(entries, cutoffs)
        assert counts["sixty_five_minutes"] == 3
        assert counts["hour"] == 2
        assert counts["sixty_seconds"] == 1

    def test_empty_entries_returns_zeros(self):
        cutoffs = {"hour": 1000.0, "sixty_five_minutes": 900.0, "sixty_seconds": 1100.0}
        counts = _count_entries_per_window([], cutoffs)
        assert counts == {"hour": 0, "sixty_five_minutes": 0, "sixty_seconds": 0}


class TestCoerceIntFromMember:
    def test_valid_member_returns_int(self):
        assert _coerce_int_from_member("100|42") == 42

    def test_invalid_member_returns_zero(self):
        result = _coerce_int_from_member("no_pipe_here")
        assert result == 0

    def test_non_numeric_value_returns_zero(self):
        result = _coerce_int_from_member("100|abc")
        assert result == 0


class TestServiceUpdaterAsosPath:
    @pytest.mark.asyncio
    async def test_update_service_time_windows_asos_uses_count_entries(self):
        metadata_store = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.zrangebyscore.return_value = [(b"member1", 1000.0), (b"member2", 2000.0)]
        updater = ServiceUpdater(metadata_store, mock_redis)

        with (
            patch(
                "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_sorted_set",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("common.time_utils.get_current_utc") as mock_time,
            patch(
                "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._count_entries_per_window",
            ) as mock_count,
            patch(
                "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._persist_counts",
            ) as mock_persist,
        ):
            mock_time.return_value = datetime(2023, 1, 1, 13, 0, 0)
            mock_count.return_value = {"hour": 2, "sixty_five_minutes": 2, "sixty_seconds": 0}
            await updater.update_service_time_windows("asos")
            mock_count.assert_called_once()
            mock_persist.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_service_time_windows_logs_on_exception(self):
        metadata_store = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.zrangebyscore.side_effect = Exception("Redis error")
        updater = ServiceUpdater(metadata_store, mock_redis)

        with (
            patch(
                "common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater._ensure_supported_sorted_set",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("common.time_utils.get_current_utc") as mock_time,
            patch("common.metadata_store_auto_updater_helpers.time_window_updater_helpers.service_updater.logger") as mock_log,
        ):
            mock_time.return_value = datetime(2023, 1, 1, 13, 0, 0)
            await updater.update_service_time_windows("test_service")
            mock_log.error.assert_called_once()
