from __future__ import annotations

"""Helper for decoding market hashes from Redis"""

from typing import Any, Dict, Optional, Tuple

from .float_utils import safe_float


class MarketHashDecoder:
    """Decodes Redis market hash data"""

    def decode_weather_market_hash(self, market_data: Dict[Any, Any]) -> Dict[str, str]:
        """
        Decode bytes in market hash to strings

        Args:
            market_data: Raw market data hash from Redis

        Returns:
            Decoded dictionary with string keys and values
        """
        return {
            (k.decode("utf-8") if isinstance(k, bytes) else k): (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in market_data.items()
        }

    def extract_strike_info(self, decoded: Dict[str, str]) -> Tuple[str, Optional[float], Optional[float]]:
        """
        Extract strike information from decoded market hash

        Args:
            decoded: Decoded market hash

        Returns:
            Tuple of (strike_type, floor_strike, cap_strike)
        """
        if "strike_type" in decoded:
            raw_strike_type = decoded["strike_type"]
        else:
            raw_strike_type = ""
        strike_type = str(raw_strike_type).lower()
        if "floor_strike" in decoded:
            floor_raw = decoded["floor_strike"]
        else:
            floor_raw = None
        if "cap_strike" in decoded:
            cap_raw = decoded["cap_strike"]
        else:
            cap_raw = None
        floor_strike = safe_float(floor_raw)
        cap_strike = safe_float(cap_raw)
        return strike_type, floor_strike, cap_strike
