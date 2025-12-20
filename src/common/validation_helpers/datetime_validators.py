"""Datetime validation helpers."""

import math
from datetime import datetime
from datetime import timezone as tz

from .exceptions import ValidationError

MAX_TIME_TO_EXPIRY_YEARS = 10.0


class DatetimeValidators:
    """Validators for datetime and time-based values."""

    @staticmethod
    def validate_datetime_object(dt: datetime | None, field_name: str = "datetime") -> bool:
        """Validate datetime object is valid and not None."""
        if dt is None:
            raise ValidationError(f"{field_name} cannot be None")
        try:
            has_tzinfo = dt.tzinfo is not None
        except AttributeError:
            raise TypeError(f"{field_name} must be datetime, got {type(dt).__name__}")
        if has_tzinfo:
            min_datetime = datetime(1970, 1, 1, tzinfo=tz.utc)
            max_datetime = datetime(2100, 1, 1, tzinfo=tz.utc)
        else:
            min_datetime = datetime(1970, 1, 1)
            max_datetime = datetime(2100, 1, 1)
        if dt < min_datetime:
            raise ValidationError(f"{field_name} {dt} is too far in the past (before 1970)")
        if dt > max_datetime:
            raise ValidationError(f"{field_name} {dt} is too far in the future (after 2100)")
        return True

    @staticmethod
    def validate_time_to_expiry(time_to_expiry: float) -> bool:
        """Validate time to expiry is positive and within reasonable bounds."""
        try:
            is_nan = math.isnan(time_to_expiry)
        except TypeError:
            raise TypeError(f"time_to_expiry must be numeric, got {type(time_to_expiry).__name__}")
        if is_nan:
            raise ValidationError("Time to expiry cannot be NaN")
        try:
            is_inf = math.isinf(time_to_expiry)
        except TypeError:
            raise TypeError(f"time_to_expiry must be numeric, got {type(time_to_expiry).__name__}")
        if is_inf:
            raise ValidationError("Time to expiry cannot be infinite")
        if time_to_expiry <= 0:
            raise ValidationError(f"Time to expiry {time_to_expiry} must be positive")
        if time_to_expiry > MAX_TIME_TO_EXPIRY_YEARS:
            raise ValidationError(
                f"Time to expiry {time_to_expiry} years exceeds maximum of {MAX_TIME_TO_EXPIRY_YEARS} years"
            )
        return True
