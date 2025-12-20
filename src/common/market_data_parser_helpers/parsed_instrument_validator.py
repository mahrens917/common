"""ParsedInstrument validation helpers."""

from __future__ import annotations

from datetime import datetime

from ..market_data_parser import DateTimeCorruptionError, ValidationError

# Constants
_MIN_VALID_YEAR = 2020
_CONST_2050 = 2050
_CONST_2099 = 2099


class ParsedInstrumentValidator:
    """Validates ParsedInstrument data after initialization."""

    @staticmethod
    def validate_option_fields(strike: float | None, option_type: str | None, raw_ticker: str) -> None:
        """
        Validate option-specific fields.

        Args:
            strike: Strike price
            option_type: Option type (call/put)
            raw_ticker: Original ticker for error messages

        Raises:
            ValidationError: If validation fails
        """
        if strike is None or option_type is None:
            raise ValidationError(f"Options must have strike and type: {raw_ticker}")

    @staticmethod
    def validate_future_fields(strike: float | None, option_type: str | None, raw_ticker: str) -> None:
        """
        Validate future-specific fields.

        Args:
            strike: Strike price (should be None)
            option_type: Option type (should be None)
            raw_ticker: Original ticker for error messages

        Raises:
            ValidationError: If validation fails
        """
        if strike is not None or option_type is not None:
            raise ValidationError(f"Futures cannot have strike or type: {raw_ticker}")

    @staticmethod
    def validate_spot_fields(strike: float | None, option_type: str | None, raw_ticker: str) -> None:
        """
        Validate spot-specific fields.

        Args:
            strike: Strike price (should be None)
            option_type: Option type (should be None)
            raw_ticker: Original ticker for error messages

        Raises:
            ValidationError: If validation fails
        """
        if strike is not None or option_type is not None:
            raise ValidationError(f"Spot pairs cannot have strike or type: {raw_ticker}")

    @staticmethod
    def validate_expiry_year(expiry_date: datetime, raw_ticker: str) -> None:
        """
        Validate expiry year for corruption.

        Args:
            expiry_date: Expiry date to check
            raw_ticker: Original ticker for error messages

        Raises:
            DateTimeCorruptionError: If year is corrupted
        """
        year = expiry_date.year

        # Spot pairs use far future date (_CONST_2099) which is acceptable
        is_corrupted = year in [2520, 2620] or (year > _CONST_2050 and year != _CONST_2099) or year < _MIN_VALID_YEAR

        if is_corrupted:
            raise DateTimeCorruptionError(f"Corrupted year detected: {year} in {raw_ticker}")
