from __future__ import annotations

"""Weather station configuration loader for Kalshi catalog."""


import json
import logging
from pathlib import Path
from typing import Any, Set

logger = logging.getLogger(__name__)


class WeatherStationLoader:
    """Loads weather station whitelist from configuration."""

    _DEFAULT_WEATHER_STATIONS: tuple[str, ...] = (
        "AUS",
        "AUSHAUS",
        "CHI",
        "DEN",
        "LAX",
        "MIA",
        "NY",
        "NYC",
        "PHIL",
        "PHL",
    )

    def __init__(self, config_root: Path) -> None:
        self._config_root = config_root

    def load_station_tokens(self) -> Set[str]:
        """Load weather station tokens from config file.

        Raises:
            FileNotFoundError: When mapping file is not found.
            json.JSONDecodeError: When mapping file has invalid JSON.
        """
        mapping_path = self._config_root / "weather_station_mapping.json"

        try:
            with mapping_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.warning("Weather station mapping file missing at %s, using defaults", mapping_path)
            return set(self._DEFAULT_WEATHER_STATIONS)
        except json.JSONDecodeError:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.warning("Invalid JSON in %s, using defaults", mapping_path)
            return set(self._DEFAULT_WEATHER_STATIONS)

        mappings = payload.get("mappings") if isinstance(payload, dict) else None
        if not isinstance(mappings, dict):
            logger.warning(
                "Weather station mapping file missing 'mappings' object at %s, using defaults",
                mapping_path,
            )
            return set(self._DEFAULT_WEATHER_STATIONS)

        tokens = self._extract_tokens_from_mappings(mappings)

        if not tokens:
            logger.warning("No station tokens found in %s, using defaults", mapping_path)
            return set(self._DEFAULT_WEATHER_STATIONS)

        logger.info("Weather station whitelist: %s", sorted(tokens))
        return tokens

    def _extract_tokens_from_mappings(self, mappings: dict) -> Set[str]:
        """Extract all tokens from mapping structure."""
        tokens: Set[str] = set()

        for code, details in mappings.items():
            self._add_code_token(tokens, code)
            if isinstance(details, dict):
                self._add_alias_tokens(tokens, details)
                self._add_icao_token(tokens, details)

        return tokens

    @staticmethod
    def _add_code_token(tokens: Set[str], code: Any) -> None:
        """Add station code to tokens if valid."""
        if isinstance(code, str):
            tokens.add(code.upper())

    @staticmethod
    def _add_alias_tokens(tokens: Set[str], details: dict) -> None:
        """Add alias tokens from details."""
        aliases = details.get("aliases")
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str):
                    tokens.add(alias.upper())

    @staticmethod
    def _add_icao_token(tokens: Set[str], details: dict) -> None:
        """Add ICAO code token from details."""
        if "icao" in details and isinstance(details["icao"], str):
            tokens.add(details["icao"].upper())
