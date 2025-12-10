"""Tests for dawn reset service logger."""

from datetime import datetime
from unittest.mock import patch

from common.dawn_reset_service_helpers.logger import DawnCheckContext, DawnResetLogger


class TestDawnCheckContext:
    """Tests for DawnCheckContext dataclass."""

    def test_dawn_check_context_creation(self) -> None:
        """DawnCheckContext can be created with all fields."""
        context = DawnCheckContext(
            latitude=40.7128,
            longitude=-74.0060,
            previous_timestamp=datetime(2024, 12, 1, 5, 0, 0),
            current_timestamp=datetime(2024, 12, 1, 8, 0, 0),
            dawn_previous=datetime(2024, 11, 30, 7, 0, 0),
            dawn_current=datetime(2024, 12, 1, 7, 0, 0),
            dawn_reset_time=datetime(2024, 12, 1, 6, 59, 0),
            is_new_day=True,
            relevant_dawn=datetime(2024, 12, 1, 6, 59, 0),
            is_cached=False,
        )

        assert context.latitude == 40.7128
        assert context.longitude == -74.0060
        assert context.is_new_day is True
        assert context.is_cached is False

    def test_dawn_check_context_is_frozen(self) -> None:
        """DawnCheckContext should be immutable (frozen)."""
        context = DawnCheckContext(
            latitude=40.7128,
            longitude=-74.0060,
            previous_timestamp=datetime(2024, 12, 1, 5, 0, 0),
            current_timestamp=datetime(2024, 12, 1, 8, 0, 0),
            dawn_previous=datetime(2024, 11, 30, 7, 0, 0),
            dawn_current=datetime(2024, 12, 1, 7, 0, 0),
            dawn_reset_time=datetime(2024, 12, 1, 6, 59, 0),
            is_new_day=True,
            relevant_dawn=datetime(2024, 12, 1, 6, 59, 0),
            is_cached=False,
        )

        try:
            context.latitude = 0.0
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass


class TestDawnResetLogger:
    """Tests for DawnResetLogger."""

    def test_log_dawn_check_cached(self) -> None:
        """Logs at debug level for cached results."""
        logger = DawnResetLogger()
        context = DawnCheckContext(
            latitude=40.7128,
            longitude=-74.0060,
            previous_timestamp=datetime(2024, 12, 1, 5, 0, 0),
            current_timestamp=datetime(2024, 12, 1, 8, 0, 0),
            dawn_previous=datetime(2024, 11, 30, 7, 0, 0),
            dawn_current=datetime(2024, 12, 1, 7, 0, 0),
            dawn_reset_time=datetime(2024, 12, 1, 6, 59, 0),
            is_new_day=True,
            relevant_dawn=datetime(2024, 12, 1, 6, 59, 0),
            is_cached=True,
        )

        with patch("common.dawn_reset_service_helpers.logger.logger") as mock_logger:
            logger.log_dawn_check(context)

            mock_logger.debug.assert_called_once()
            mock_logger.info.assert_not_called()

    def test_log_dawn_check_new_day_not_cached(self) -> None:
        """Logs at info level for new day, not cached."""
        logger = DawnResetLogger()
        context = DawnCheckContext(
            latitude=40.7128,
            longitude=-74.0060,
            previous_timestamp=datetime(2024, 12, 1, 5, 0, 0),
            current_timestamp=datetime(2024, 12, 1, 8, 0, 0),
            dawn_previous=datetime(2024, 11, 30, 7, 0, 0),
            dawn_current=datetime(2024, 12, 1, 7, 0, 0),
            dawn_reset_time=datetime(2024, 12, 1, 6, 59, 0),
            is_new_day=True,
            relevant_dawn=datetime(2024, 12, 1, 6, 59, 0),
            is_cached=False,
        )

        with patch("common.dawn_reset_service_helpers.logger.logger") as mock_logger:
            logger.log_dawn_check(context)

            assert mock_logger.info.call_count >= 1

    def test_log_dawn_check_not_new_day(self) -> None:
        """Does not log info for non-new day."""
        logger = DawnResetLogger()
        context = DawnCheckContext(
            latitude=40.7128,
            longitude=-74.0060,
            previous_timestamp=datetime(2024, 12, 1, 5, 0, 0),
            current_timestamp=datetime(2024, 12, 1, 5, 30, 0),
            dawn_previous=datetime(2024, 11, 30, 7, 0, 0),
            dawn_current=datetime(2024, 12, 1, 7, 0, 0),
            dawn_reset_time=datetime(2024, 12, 1, 6, 59, 0),
            is_new_day=False,
            relevant_dawn=None,
            is_cached=False,
        )

        with patch("common.dawn_reset_service_helpers.logger.logger") as mock_logger:
            logger.log_dawn_check(context)

            mock_logger.info.assert_not_called()
