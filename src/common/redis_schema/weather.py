from __future__ import annotations

"""Weather-related Redis key helpers."""


import re
from dataclasses import dataclass

from common.exceptions import ValidationError

from .namespaces import KeyBuilder, RedisNamespace, sanitize_segment
from .validators import register_namespace

register_namespace("weather:station:", "Latest weather station snapshots")
register_namespace("weather:station_history:", "Historical weather observations")
register_namespace("weather:station_alerts:", "Active weather station alerts")
register_namespace("weather:daily_high:", "Daily high temperatures by station and date")

_ICAO_RE = re.compile(r"^[A-Z0-9_.\-]+$")


def ensure_uppercase_icao(code: str) -> str:
    """Return the validated ICAO code, raising if the value is not strict uppercase."""

    normalized = code.strip()
    if not normalized:
        raise ValueError("ICAO code cannot be empty")

    if normalized != normalized.upper():
        raise TypeError(f"ICAO code must be uppercase: {code!r}")

    if not _ICAO_RE.fullmatch(normalized):
        raise ValidationError(f"ICAO code contains invalid characters: {code!r}")

    return normalized


@dataclass(frozen=True)
class WeatherStationKey:
    """Key for latest weather data (hash)."""

    icao: str

    def key(self) -> str:
        icao = ensure_uppercase_icao(self.icao)
        segments = ["station", sanitize_segment(icao, case="unchanged")]
        builder = KeyBuilder(RedisNamespace.WEATHER, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class WeatherHistoryKey:
    """Key for weather history sorted set/hash."""

    icao: str

    def key(self) -> str:
        icao = ensure_uppercase_icao(self.icao)
        segments = ["station_history", sanitize_segment(icao, case="unchanged")]
        builder = KeyBuilder(RedisNamespace.WEATHER, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class WeatherAlertKey:
    """Key for station-specific alerting state."""

    icao: str
    alert_type: str

    def key(self) -> str:
        icao = ensure_uppercase_icao(self.icao)
        segments = [
            "station_alerts",
            sanitize_segment(icao, case="unchanged"),
            sanitize_segment(self.alert_type),
        ]
        builder = KeyBuilder(RedisNamespace.WEATHER, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class WeatherDailyHighKey:
    """Key for daily high temperature storage."""

    icao: str
    date_str: str  # Format: YYYY-MM-DD

    def key(self) -> str:
        icao = ensure_uppercase_icao(self.icao)
        segments = ["daily_high", sanitize_segment(icao, case="unchanged"), self.date_str]
        builder = KeyBuilder(RedisNamespace.WEATHER, tuple(segments))
        return builder.render()
