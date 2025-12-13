"""Field reset application with alert notification."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, cast

from common.truthy import pick_if


@dataclass(frozen=True)
class FieldResetContext:
    """Context for field reset operations."""

    field_name: str
    current_value: Any
    previous_data: Dict[str, Any]
    latitude: float
    longitude: float
    station_id: str
    current_timestamp: Optional[datetime] = None


class FieldResetApplicatorWithAlert:
    """Applies field resets with alert notifications."""

    def __init__(
        self,
        field_reset_manager: Any,
        alert_manager: Any,
        daily_reset_fields: set,
        should_reset_callback,
    ):
        self.field_reset_manager = field_reset_manager
        self.alert_manager = alert_manager
        self.daily_reset_fields = daily_reset_fields
        self.should_reset_callback = should_reset_callback

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
        if isinstance(field_name, FieldResetContext):
            context = field_name
        else:
            resolved_previous_data = pick_if(previous_data is None, dict, lambda: cast(Dict[str, Any], previous_data))
            resolved_latitude = pick_if(latitude is None, float, lambda: cast(float, latitude))
            resolved_longitude = pick_if(longitude is None, float, lambda: cast(float, longitude))
            context = FieldResetContext(
                field_name=field_name,
                current_value=current_value,
                previous_data=resolved_previous_data,
                latitude=resolved_latitude,
                longitude=resolved_longitude,
                station_id=station_id,
                current_timestamp=current_timestamp,
            )

        return await self._apply_field_resets_with_alert(
            field_name=context.field_name,
            current_value=context.current_value,
            previous_data=context.previous_data,
            latitude=context.latitude,
            longitude=context.longitude,
            station_id=context.station_id,
            current_timestamp=context.current_timestamp,
        )

    async def _apply_field_resets_with_alert(
        self,
        field_name: str,
        current_value: Any,
        previous_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        station_id: str,
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[Any, bool, Optional[datetime]]:
        if field_name not in self.daily_reset_fields:
            return current_value, False, None

        should_reset, boundary = self.should_reset_callback(
            field_name,
            latitude,
            longitude,
            previous_data,
            current_timestamp,
        )

        await self._send_reset_alert(
            station_id,
            field_name,
            should_reset,
            previous_data.get(field_name),
            current_value,
        )

        final_value = self.field_reset_manager.apply_reset_logic(field_name, current_value, previous_data, should_reset)

        return final_value, should_reset, boundary

    async def _send_reset_alert(self, station_id: str, field_name: str, was_reset: bool, previous_value: Any, new_value: Any) -> None:
        await self.alert_manager.send_reset_alert(station_id, field_name, was_reset, previous_value, new_value)
