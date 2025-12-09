from __future__ import annotations

"""
Helpers for loading station-level temperature precision metadata.

The manifest path is declared in ``config/weather_precision_settings.json`` using the
``WEATHER_PRECISION_CONFIG_PATH`` entry, and the manifest itself defaults to
``config/weather_station_precision.json``. These values are treated as canonical across
collectors, Redis ingestion, and model training.
"""


import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Literal

from src.common.redis_schema import ensure_uppercase_icao

_PRECISION_SETTINGS_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "weather_precision_settings.json"
)
_PRECISION_CONFIG_ENV = "WEATHER_PRECISION_CONFIG_PATH"

PrecisionSource = Literal["metar", "asos"]


class PrecisionConfigError(RuntimeError):
    """Raised when precision metadata is missing or malformed."""

    default_message = "Precision configuration error"

    def __init__(self, *, detail: str) -> None:
        super().__init__(f"{self.default_message}: {detail}")

    @classmethod
    def manifest_override_missing(cls, path: Path) -> "PrecisionConfigError":
        return cls(detail=f"{_PRECISION_CONFIG_ENV} points to non-existent path: {path}")

    @classmethod
    def settings_file_missing(cls) -> "PrecisionConfigError":
        return cls(detail=f"Precision settings file not found: {_PRECISION_SETTINGS_PATH}")

    @classmethod
    def settings_missing_manifest(cls) -> "PrecisionConfigError":
        return cls(detail=f"{_PRECISION_CONFIG_ENV} missing from {_PRECISION_SETTINGS_PATH}")

    @classmethod
    def manifest_missing(cls, path: Path) -> "PrecisionConfigError":
        return cls(detail=f"Precision manifest not found: {path}")

    @classmethod
    def invalid_stations_mapping(cls) -> "PrecisionConfigError":
        return cls(detail="Precision config must define a 'stations' mapping")

    @classmethod
    def station_entry_not_mapping(cls, station: str) -> "PrecisionConfigError":
        return cls(detail=f"Precision entry for {station} must be a mapping")

    @classmethod
    def invalid_icao(cls, station: str) -> "PrecisionConfigError":
        return cls(detail=f"Invalid ICAO '{station}' in precision config")

    @classmethod
    def metar_precision_invalid(cls, icao: str) -> "PrecisionConfigError":
        return cls(detail=f"{icao} metar_precision_c must be positive float")

    @classmethod
    def asos_precision_invalid(cls, icao: str) -> "PrecisionConfigError":
        return cls(detail=f"{icao} asos_precision_c must be positive float")

    @classmethod
    def unsupported_source(cls, source: object) -> "PrecisionConfigError":
        return cls(detail=f"Unsupported precision source '{source}'")

    @classmethod
    def station_metadata_missing(cls, icao: str) -> "PrecisionConfigError":
        return cls(
            detail=(
                f"No precision metadata for station {icao}; update weather_station_precision.json"
            )
        )


def _resolve_precision_manifest_path() -> Path:
    env_override = os.getenv(_PRECISION_CONFIG_ENV)
    if env_override:
        manifest_path = Path(env_override).expanduser().resolve()
        if not manifest_path.exists():
            raise PrecisionConfigError.manifest_override_missing(manifest_path)
        return manifest_path

    if not _PRECISION_SETTINGS_PATH.exists():
        raise PrecisionConfigError.settings_file_missing()

    with _PRECISION_SETTINGS_PATH.open("r", encoding="utf-8") as handle:
        settings = json.load(handle)

    manifest_entry = settings.get(_PRECISION_CONFIG_ENV)
    if not manifest_entry:
        raise PrecisionConfigError.settings_missing_manifest()

    manifest_path = Path(manifest_entry)
    if not manifest_path.is_absolute():
        repo_root = _PRECISION_SETTINGS_PATH.parents[1]
        manifest_path = (repo_root / manifest_path).resolve()

    if not manifest_path.exists():
        raise PrecisionConfigError.manifest_missing(manifest_path)

    return manifest_path


@lru_cache(maxsize=1)
def _load_precision_config() -> Dict[str, Dict[str, float]]:
    manifest_path = _resolve_precision_manifest_path()

    with manifest_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    stations = payload.get("stations")
    if not isinstance(stations, dict):
        raise PrecisionConfigError.invalid_stations_mapping()

    normalized: Dict[str, Dict[str, float]] = {}
    for station, precisions in stations.items():
        if not isinstance(precisions, dict):
            raise PrecisionConfigError.station_entry_not_mapping(station)

        try:
            icao = ensure_uppercase_icao(str(station))
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise PrecisionConfigError.invalid_icao(station) from exc

        metar_precision = precisions.get("metar_precision_c")
        asos_precision = precisions.get("asos_precision_c")

        if not isinstance(metar_precision, (int, float)) or metar_precision <= 0:
            raise PrecisionConfigError.metar_precision_invalid(icao)
        if not isinstance(asos_precision, (int, float)) or asos_precision <= 0:
            raise PrecisionConfigError.asos_precision_invalid(icao)

        normalized[icao] = {
            "metar_precision_c": float(metar_precision),
            "asos_precision_c": float(asos_precision),
        }

    return normalized


def get_temperature_precision(icao_code: str, source: PrecisionSource) -> float:
    """
    Return the configured temperature precision for the given station and source.

    Args:
        icao_code: ICAO identifier (case-insensitive).
        source: Either ``"metar"`` or ``"asos"``.
    """
    if source not in ("metar", "asos"):
        raise PrecisionConfigError.unsupported_source(source)

    station = ensure_uppercase_icao(str(icao_code))
    stations = _load_precision_config()

    if station not in stations:
        raise PrecisionConfigError.station_metadata_missing(station)

    if source == "metar":
        key = "metar_precision_c"
    else:
        key = "asos_precision_c"
    return stations[station][key]


def get_metar_precision(icao_code: str) -> float:
    """Convenience helper for METAR precision."""

    return get_temperature_precision(icao_code, "metar")


def get_asos_precision(icao_code: str) -> float:
    """Convenience helper for ASOS precision."""

    return get_temperature_precision(icao_code, "asos")


__all__ = [
    "PrecisionConfigError",
    "get_asos_precision",
    "get_metar_precision",
    "get_temperature_precision",
]
