"""Extract optional fields from trade data."""

from typing import Any, Dict

from .codec_helpers.field_extractor import load_datetime


class OptionalFieldExtractor:
    """Extracts and converts optional fields from trade data."""

    @staticmethod
    def extract(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and convert optional fields from data."""
        last_update = load_datetime(data.get("last_price_update"))
        settlement_time = load_datetime(data.get("settlement_time"))

        settlement_price = data.get("settlement_price_cents")
        if settlement_price is not None:
            settlement_price = int(settlement_price)

        return {
            "weather_station": data.get("weather_station"),
            "last_yes_bid": data.get("last_yes_bid"),
            "last_yes_ask": data.get("last_yes_ask"),
            "last_price_update": last_update,
            "settlement_price_cents": settlement_price,
            "settlement_time": settlement_time,
        }
