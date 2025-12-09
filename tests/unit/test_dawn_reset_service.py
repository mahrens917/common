"""Tests for dawn reset service module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.dawn_reset_service import DawnResetService


class TestDawnResetServiceInit:
    """Tests for DawnResetService initialization."""

    def test_init_creates_dependencies(self) -> None:
        """Initialization creates all dependencies."""
        service = DawnResetService()

        assert service.dawn_calculator is not None
        assert service.cache_manager is not None
        assert service.timestamp_resolver is not None
        assert service.field_reset_manager is not None
        assert service.alert_manager is not None
        assert service.logger is not None

    def test_init_accepts_telegram_handler(self) -> None:
        """Accepts telegram handler."""
        mock_handler = MagicMock()
        service = DawnResetService(telegram_handler=mock_handler)

        assert service.alert_manager is not None

    def test_init_accepts_dependencies(self) -> None:
        """Accepts provided dependencies."""
        mock_deps = MagicMock()
        mock_deps.dawn_calculator = MagicMock()
        mock_deps.cache_manager = MagicMock()
        mock_deps.timestamp_resolver = MagicMock()
        mock_deps.field_reset_manager = MagicMock()
        mock_deps.alert_manager = MagicMock()
        mock_deps.logger = MagicMock()

        service = DawnResetService(dependencies=mock_deps)

        assert service.dawn_calculator is mock_deps.dawn_calculator


class TestDawnResetServiceIsNewTradingDay:
    """Tests for DawnResetService.is_new_trading_day."""

    def test_delegates_to_trading_day_checker(self) -> None:
        """Delegates to internal trading day checker."""
        service = DawnResetService()
        service._trading_day_checker = MagicMock()
        service._trading_day_checker.is_new_trading_day.return_value = (True, datetime.now())

        prev_ts = datetime(2024, 12, 1, 5, 0, 0)
        curr_ts = datetime(2024, 12, 1, 8, 0, 0)

        result = service.is_new_trading_day(40.7128, -74.0060, prev_ts, curr_ts)

        service._trading_day_checker.is_new_trading_day.assert_called_once_with(
            40.7128, -74.0060, prev_ts, curr_ts
        )
        assert result[0] is True


class TestDawnResetServiceShouldResetField:
    """Tests for DawnResetService.should_reset_field."""

    def test_delegates_to_field_reset_manager(self) -> None:
        """Delegates to field reset manager."""
        service = DawnResetService()
        service.field_reset_manager = MagicMock()
        service.field_reset_manager.should_reset_field.return_value = (True, datetime.now())

        previous_data = {"last_dawn_reset": "2024-12-01T05:00:00"}

        result = service.should_reset_field(
            "max_temp",
            40.7128,
            -74.0060,
            previous_data,
        )

        service.field_reset_manager.should_reset_field.assert_called_once()
        assert result[0] is True


class TestDawnResetServiceApplyFieldResets:
    """Tests for DawnResetService.apply_field_resets_with_alert."""

    @pytest.mark.asyncio
    async def test_delegates_to_field_reset_applicator(self) -> None:
        """Delegates to field reset applicator."""
        service = DawnResetService()
        service._field_reset_applicator = AsyncMock()
        service._field_reset_applicator.apply_field_resets_with_alert.return_value = (
            None,
            True,
            datetime.now(),
        )

        result = await service.apply_field_resets_with_alert(
            "max_temp",
            current_value=75.0,
            previous_data={"last_dawn_reset": "2024-12-01T05:00:00"},
            latitude=40.7128,
            longitude=-74.0060,
            station_id="KJFK",
        )

        service._field_reset_applicator.apply_field_resets_with_alert.assert_called_once()
        assert result[1] is True


class TestDawnResetServiceConstants:
    """Tests for DawnResetService constants."""

    def test_daily_reset_fields_defined(self) -> None:
        """DAILY_RESET_FIELDS is defined."""
        assert hasattr(DawnResetService, "DAILY_RESET_FIELDS")

    def test_clear_on_reset_fields_defined(self) -> None:
        """CLEAR_ON_RESET_FIELDS is defined."""
        assert hasattr(DawnResetService, "CLEAR_ON_RESET_FIELDS")

    def test_last_dawn_reset_field_defined(self) -> None:
        """LAST_DAWN_RESET_FIELD is defined."""
        assert hasattr(DawnResetService, "LAST_DAWN_RESET_FIELD")
