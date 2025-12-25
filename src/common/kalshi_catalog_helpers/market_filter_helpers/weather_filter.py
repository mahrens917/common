"""Weather market filtering."""

from typing import Dict, Optional, Set


class WeatherFilter:
    """Filters weather markets."""

    def __init__(self, weather_station_tokens: Set[str]):
        """Initialize with weather station tokens."""
        self._weather_station_tokens = weather_station_tokens

    def passes_filters(self, market: Dict[str, object], now_ts: float, close_time_validator) -> bool:
        """Check if weather market passes filters."""
        ticker_val = market.get("ticker")
        if ticker_val:
            ticker = str(ticker_val).upper()
        else:
            ticker = ""
        if not ticker.startswith("KXHIGH"):
            return False
        if not close_time_validator.is_in_future(market, now_ts):
            return False
        station_token = self.extract_station_token(ticker)
        if station_token is None:
            return False
        if self._weather_station_tokens and station_token not in self._weather_station_tokens:
            return False
        return True

    @staticmethod
    def extract_station_token(ticker: str) -> Optional[str]:
        """Extract weather station token from ticker."""
        suffix = ticker[len("KXHIGH") :]
        if not suffix:
            return None

        station = suffix.split("-", 1)[0]
        return station.upper() if station else None
