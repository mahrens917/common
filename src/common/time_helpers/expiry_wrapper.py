from __future__ import annotations

"""DateTimeExpiry wrapper class."""


from datetime import datetime
from numbers import Real
from typing import Union

from src.common.exceptions import ValidationError

from .expiry_conversions import (
    get_datetime_from_time_point,
    get_time_from_epoch,
    parse_iso_datetime,
)


class DateTimeExpiry:
    """Encapsulate datetime representation of expiry dates."""

    datetime_value: datetime

    def __init__(self, expiry_value: Union[datetime, str, float, "DateTimeExpiry"]):
        if isinstance(expiry_value, DateTimeExpiry):
            self.datetime_value = expiry_value.datetime_value
        elif isinstance(expiry_value, datetime):
            self.datetime_value = expiry_value
        elif isinstance(expiry_value, str):
            result = parse_iso_datetime(expiry_value)
            if result:
                self.datetime_value = result[0]
            else:  # pragma: no cover - defensive
                raise ValidationError(f"Invalid expiry format: {expiry_value}")
        elif isinstance(expiry_value, Real):
            self.datetime_value = get_datetime_from_time_point(float(expiry_value))
        else:  # pragma: no cover - defensive
            raise TypeError(f"Unsupported expiry type: {type(expiry_value)}")

    @property
    def time_point(self) -> float:
        return get_time_from_epoch(self.datetime_value)

    @property
    def iso_string(self) -> str:
        return self.datetime_value.isoformat()

    def _to_datetime(self, other):
        """Convert comparison operand to datetime."""
        if isinstance(other, DateTimeExpiry):
            return other.datetime_value
        if isinstance(other, datetime):
            return other
        if isinstance(other, str):
            try:
                return datetime.fromisoformat(other.replace("Z", "+00:00"))
            except (
                ValueError,
                TypeError,
            ):
                return None
        if isinstance(other, (int, float)):
            return get_datetime_from_time_point(float(other))
        return NotImplemented

    def __eq__(self, other):
        other_dt = self._to_datetime(other)
        if other_dt is NotImplemented:
            return NotImplemented
        if other_dt is None:
            return False
        return self.datetime_value == other_dt

    def __lt__(self, other):
        other_dt = self._to_datetime(other)
        if other_dt is NotImplemented:
            return NotImplemented
        if other_dt is None:
            return False
        return self.datetime_value < other_dt

    def __le__(self, other):
        return self < other or self == other

    def __gt__(self, other):
        other_dt = self._to_datetime(other)
        if other_dt is NotImplemented:
            return NotImplemented
        if other_dt is None:
            return False
        return self.datetime_value > other_dt

    def __ge__(self, other):
        return self > other or self == other

    def __str__(self) -> str:
        return self.iso_string

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"DateTimeExpiry(dt={self.datetime_value})"

    def __hash__(self) -> int:
        return hash(self.datetime_value)
