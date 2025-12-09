"""Field extraction utilities for trade record codec."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def ensure_timezone(dt: datetime) -> datetime:
    """Attach UTC timezone information when the payload omits it."""
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


def load_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime string with timezone handling."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return ensure_timezone(parsed)


def extract_optional_fields(data: Dict[str, Any]) -> Dict[str, Any]:
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
