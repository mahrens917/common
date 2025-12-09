from __future__ import annotations

"""Weather station mapping helpers used by trading services."""


import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional

from src.common.config.weather import (
    WeatherConfigError,
)
from src.common.config.weather import (
    load_weather_station_mapping as _load_config_weather_station_mapping,
)

MAPPINGS_KEY = "mappings"
WEATHER_MAPPING_FILENAME = "weather_station_mapping.json"


# Constants
_CONST_4 = 4


def _default_mapping_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / WEATHER_MAPPING_FILENAME


def _load_mapping_from_path(mapping_path: Path) -> Dict[str, Dict]:
    try:
        with open(mapping_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise WeatherConfigError(f"Weather station mapping file not found: {mapping_path}") from exc
    except json.JSONDecodeError as exc:
        raise WeatherConfigError(f"Weather station mapping JSON invalid ({mapping_path})") from exc
    except OSError as exc:  # pragma: no cover - filesystem errors already surfaced
        raise WeatherConfigError(f"Unable to read weather station mapping {mapping_path}") from exc

    mappings = payload.get(MAPPINGS_KEY)
    if not isinstance(mappings, dict):
        raise WeatherConfigError("weather_station_mapping.json missing 'mappings' object")
    return mappings


def load_weather_station_mapping(path: Optional[Path] = None) -> Dict[str, Dict]:
    """
    Load weather station mapping data from JSON.

    Args:
        path: Optional explicit file path; if omitted, falls back to configured project mapping.

    Returns:
        Dictionary keyed by canonical city codes.

    Raises:
        WeatherConfigError: When the mapping file is missing or malformed.
    """
    if path is not None:
        return _load_mapping_from_path(path)

    return _load_config_weather_station_mapping()


def _build_alias_map(mapping: Mapping[str, Mapping]) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    for city_code, station_info in mapping.items():
        canonical = city_code.upper()
        alias_map[canonical] = city_code
        aliases = station_info.get("aliases")
        if isinstance(aliases, Iterable):
            for alias in aliases:
                if not isinstance(alias, str):
                    continue
                alias_map[alias.upper()] = city_code
    return alias_map


def _build_icao_map(mapping: Mapping[str, Mapping]) -> Dict[str, str]:
    icao_map: Dict[str, str] = {}
    for city_code, station_info in mapping.items():
        icao = station_info.get("icao")
        if isinstance(icao, str) and icao:
            icao_map[icao] = city_code
    return icao_map


@dataclass
class WeatherStationResolver:
    """
    Resolve Kalshi weather market tickers to canonical weather stations.
    """

    mapping: Dict[str, Dict]

    def __init__(self, mapping: Optional[Dict[str, Dict]] = None) -> None:
        self.mapping = mapping if mapping is not None else load_weather_station_mapping()
        self._alias_map = _build_alias_map(self.mapping)
        self._icao_map = _build_icao_map(self.mapping)

    @property
    def alias_map(self) -> Dict[str, str]:
        return dict(self._alias_map)

    @property
    def icao_to_city_map(self) -> Dict[str, str]:
        return dict(self._icao_map)

    def refresh(self, mapping: Dict[str, Dict]) -> None:
        """Replace mapping and rebuild lookups."""
        self.mapping = mapping
        self._alias_map = _build_alias_map(mapping)
        self._icao_map = _build_icao_map(mapping)

    def resolve_ticker(self, market_ticker: str) -> str:
        """
        Resolve a Kalshi weather market ticker (e.g. 'KXHIGHNYC-25AUG31-B79.5')
        to the four-letter ICAO-style weather station code.
        """
        if not market_ticker.startswith("KXHIGH"):
            raise ValueError(f"Market ticker must start with KXHIGH: {market_ticker}")

        suffix = market_ticker[len("KXHIGH") :]
        dash_index = suffix.find("-")
        if dash_index <= 0:
            raise ValueError(f"Invalid market ticker format: {market_ticker}")

        city_token = suffix[:dash_index].upper()
        canonical_city = self._alias_map.get(city_token, city_token)

        station_info = self.mapping.get(canonical_city)
        if station_info is None:
            raise ValueError(
                f"Weather station '{canonical_city}' not found in mapping for ticker {market_ticker}"
            )

        icao_code = station_info.get("icao")
        if not isinstance(icao_code, str) or not icao_code:
            raise ValueError(
                f"Weather station mapping for '{canonical_city}' missing ICAO code (ticker {market_ticker})"
            )

        normalized_icao = icao_code.upper()
        if len(normalized_icao) != _CONST_4 or not normalized_icao.startswith("K"):
            raise ValueError(
                f"Invalid ICAO code '{normalized_icao}' for station '{canonical_city}' (ticker {market_ticker})"
            )

        return normalized_icao
