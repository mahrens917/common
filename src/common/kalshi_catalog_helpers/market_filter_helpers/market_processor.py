"""Market processing logic."""

from typing import Dict, List, Optional

from .close_time_validator import CloseTimeValidator
from .crypto_detector import CryptoMarketDetector
from .crypto_validator import validate_crypto_strikes, validate_crypto_ticker
from .weather_filter import WeatherFilter


class MarketProcessor:
    """Processes individual markets and updates statistics."""

    def __init__(
        self,
        crypto_detector: CryptoMarketDetector,
        weather_filter: WeatherFilter,
        close_time_validator: CloseTimeValidator,
    ):
        self._crypto_detector = crypto_detector
        self._weather_filter = weather_filter
        self._close_time_validator = close_time_validator

    def process_market(
        self,
        market: Dict[str, object],
        filtered: List[Dict[str, object]],
        stats: Dict[str, int],
        now_ts: float,
    ) -> None:
        """Process single market and update stats."""
        category = market.get("__category")
        ticker_val = market.get("ticker")
        if ticker_val:
            ticker = str(ticker_val)
        else:
            ticker = ""

        if self._is_crypto_market(market, category):
            self._process_crypto_market(market, filtered, stats, now_ts)
        elif self._is_weather_market(category, ticker):
            self._process_weather_market(market, filtered, stats, now_ts)
        else:
            stats["other_total"] += 1

    def _is_crypto_market(self, market: Dict[str, object], category: Optional[object]) -> bool:
        """Check if market is crypto-related."""
        return category == "Crypto" or self._crypto_detector.is_crypto_market(market)

    @staticmethod
    def _is_weather_market(category: Optional[object], ticker: str) -> bool:
        """Check if market is weather-related."""
        return category in {"Weather", "Climate and Weather"} or ticker.startswith("KXHIGH")

    def _process_crypto_market(
        self,
        market: Dict[str, object],
        filtered: List[Dict[str, object]],
        stats: Dict[str, int],
        now_ts: float,
    ) -> None:
        """Process crypto market and update stats."""
        stats["crypto_total"] += 1
        if self._passes_crypto_filters(market, now_ts):
            filtered.append(market)
            stats["crypto_kept"] += 1

    def _passes_crypto_filters(self, market: Dict[str, object], now_ts: float) -> bool:
        """Check if crypto market passes all filters."""
        ticker_val = market.get("ticker")
        if ticker_val:
            ticker = str(ticker_val).upper()
        else:
            ticker = ""

        if not validate_crypto_ticker(ticker):
            return False
        if not self._close_time_validator.is_in_future(market, now_ts):
            return False

        strike_type = market.get("strike_type")
        valid_strike_types = ("greater", "less", "greater_or_equal", "less_or_equal", "between")
        if strike_type not in valid_strike_types:
            return False

        return validate_crypto_strikes(market)

    def _process_weather_market(
        self,
        market: Dict[str, object],
        filtered: List[Dict[str, object]],
        stats: Dict[str, int],
        now_ts: float,
    ) -> None:
        """Process weather market and update stats."""
        stats["weather_total"] += 1
        if self._weather_filter.passes_filters(market, now_ts, self._close_time_validator):
            filtered.append(market)
            stats["weather_kept"] += 1
