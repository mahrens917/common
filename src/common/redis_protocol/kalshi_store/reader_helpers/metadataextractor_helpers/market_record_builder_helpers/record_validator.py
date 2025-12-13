"""Validate market record fields."""

from datetime import datetime
from typing import Any, Dict

from ....market_skip import MarketSkip


class RecordValidator:
    """Validates market record fields."""

    @staticmethod
    def validate_raw_hash(raw_hash: Dict[str, Any], market_ticker: str) -> None:
        """Validate raw hash is not empty."""
        if not raw_hash:
            raise MarketSkip("missing_metadata", f"No Redis hash for {market_ticker}")

    @staticmethod
    def validate_market_status(combined: Dict[str, Any], market_ticker: str, type_converter) -> None:
        """Validate market is not settled or closed."""
        status_value = type_converter.string_or_default(combined.get("status"))
        status_text = status_value.lower()
        if status_text in {"settled", "closed"}:
            raise MarketSkip("settled", f"Market {market_ticker} has status={status_text}")

    @staticmethod
    def validate_not_expired(normalized_close: str, market_ticker: str, now: datetime) -> None:
        """Validate market has not expired."""
        try:
            close_dt = datetime.fromisoformat(normalized_close.replace("Z", "+00:00"))
        except ValueError:  # policy_guard: allow-silent-handler
            close_dt = None

        if close_dt and close_dt <= now:
            raise MarketSkip("expired", f"Market {market_ticker} expired at {normalized_close}")

    @staticmethod
    def validate_close_time(close_time_value, market_ticker: str) -> None:
        """Validate close time exists."""
        if close_time_value in (None, "", b""):
            raise MarketSkip("missing_close_time", f"Market {market_ticker} missing close_time")

    @staticmethod
    def validate_strike(strike_value, market_ticker: str) -> None:
        """Validate strike value exists."""
        if strike_value is None:
            raise MarketSkip("missing_strike", f"Market {market_ticker} missing strike metadata")
