"""
Dawn reset service for handling daily field resets at local dawn.

This service provides consistent local dawn reset logic for weather-related fields
that need to reset when trading opens (at dawn) rather than at midnight.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from common.exceptions import DataError

from .dawn_reset_service_helpers import (
    FieldResetApplicatorWithAlert,
    FieldResetManager,
    TimestampResolver,
    TradingDayChecker,
)
from .dawn_reset_service_helpers.dependencies_factory import (
    DawnResetServiceDependencies,
    DawnResetServiceDependenciesFactory,
)
from .time_utils import calculate_dawn_utc


class DawnResetService:
    """Centralized service for handling local dawn field resets."""

    DAILY_RESET_FIELDS = TimestampResolver.DAILY_RESET_FIELDS
    CLEAR_ON_RESET_FIELDS = FieldResetManager.CLEAR_ON_RESET_FIELDS
    LAST_DAWN_RESET_FIELD = TimestampResolver.LAST_DAWN_RESET_FIELD

    def __init__(
        self,
        telegram_handler=None,
        *,
        dependencies: Optional[DawnResetServiceDependencies] = None,
    ):
        deps = dependencies or DawnResetServiceDependenciesFactory.create(telegram_handler, calculate_dawn_fn=calculate_dawn_utc)
        self.dawn_calculator = deps.dawn_calculator
        self.cache_manager = deps.cache_manager
        self.timestamp_resolver = deps.timestamp_resolver
        self.field_reset_manager = deps.field_reset_manager
        self.alert_manager = deps.alert_manager
        self.logger = deps.logger
        self._trading_day_checker = TradingDayChecker(deps.dawn_calculator, deps.cache_manager, deps.logger)
        self._field_reset_applicator = FieldResetApplicatorWithAlert(
            deps.field_reset_manager,
            deps.alert_manager,
            self.DAILY_RESET_FIELDS,
            self._should_reset_field,
        )

    def is_new_trading_day(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        """Check if we've crossed into a new trading day at local dawn."""
        return self._trading_day_checker.is_new_trading_day(latitude, longitude, previous_timestamp, current_timestamp)

    def _should_reset_field(
        self,
        field_name: str,
        latitude: float,
        longitude: float,
        previous_data: Dict[str, Any],
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        try:
            return self.field_reset_manager.should_reset_field(field_name, latitude, longitude, previous_data, current_timestamp)
        except DataError as exc:
            # Align with historical behaviour expected by consumers/tests: surface parsing errors as ValueError
            raise ValueError(str(exc)) from exc

    def should_reset_field(
        self,
        field_name: str,
        latitude: float,
        longitude: float,
        previous_data: Dict[str, Any],
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        """Public wrapper for _should_reset_field."""
        return self._should_reset_field(field_name, latitude, longitude, previous_data, current_timestamp)

    async def apply_field_resets_with_alert(
        self,
        field_name: Any,
        current_value: Any = None,
        previous_data: Optional[Dict[str, Any]] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        station_id: str = "",
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[Any, bool, Optional[datetime]]:
        """Handle reset flow for either a context object or explicit parameters."""
        return await self._field_reset_applicator.apply_field_resets_with_alert(
            field_name,
            current_value,
            previous_data,
            latitude,
            longitude,
            station_id,
            current_timestamp,
        )
