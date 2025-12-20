from __future__ import annotations

"""Helper for resolving city tokens from ICAO codes"""


import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("src.monitor.chart_generator")


class CityTokenResolver:
    """Resolves Kalshi city tokens from weather station ICAO codes"""

    def _load_mapping_data(self):
        """Load weather station mapping from config file."""
        cg_module = sys.modules.get("src.monitor.chart_generator")
        os_module = getattr(cg_module, "os", os)
        open_fn = getattr(cg_module, "open", open)

        try:
            base_path = Path(__file__).parents[3]
        except IndexError as exc:
            raise OSError("Unable to resolve weather station mapping path") from exc

        config_path = os_module.path.join(str(base_path), "config", "weather_station_mapping.json")

        with open_fn(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_tokens_for_station(
        self, icao_code: str, mapping_data: dict
    ) -> Tuple[List[str], Optional[str]]:
        """Extract tokens and canonical token for a given ICAO code."""
        for city_code, station_data in mapping_data["mappings"].items():
            # Check if station matches the ICAO code
            if "icao" in station_data and station_data["icao"] == icao_code:
                tokens = [city_code]
                # Aliases are optional
                aliases = station_data["aliases"] if "aliases" in station_data else []
                if isinstance(aliases, list):
                    tokens.extend(alias for alias in aliases if isinstance(alias, str))
                tokens.append(icao_code)
                tokens = [token.upper() for token in tokens]
                return tokens, city_code.upper()
        return [], None

    async def get_city_tokens_for_icao(self, icao_code: str) -> Tuple[List[str], Optional[str]]:
        """
        Get all known Kalshi tokens (aliases + ICAO) and canonical token

        Args:
            icao_code: ICAO code for weather station

        Returns:
            Tuple of (all_tokens, canonical_token)
        """
        try:
            mapping_data = self._load_mapping_data()
            return self._extract_tokens_for_station(icao_code, mapping_data)
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
        ):
            logger.warning(f"Failed to load weather station mapping")
            return [], None
