"""Instrument type-specific parsing helpers."""

from datetime import datetime, timezone

from ..market_data_parser import ParsedInstrument, ParsingError
from .date_parser import DeribitDateParser
from .symbol_validator import SymbolValidator


class OptionParser:
    """Parses option instruments."""

    @staticmethod
    def parse(symbol: str, date_part: str, strike_str: str, option_type: str, ticker: str) -> ParsedInstrument:
        """
        Parse option instrument.

        Args:
            symbol: Symbol (BTC/ETH)
            date_part: Date string
            strike_str: Strike price string
            option_type: Option type (C/P)
            ticker: Original ticker

        Returns:
            ParsedInstrument

        Raises:
            ParsingError: If parsing fails
        """
        expiry_date = DeribitDateParser.parse_date(date_part)

        try:
            strike = float(strike_str)
        except ValueError:
            raise ParsingError(f"Invalid strike price: {strike_str}")

        # Convert single letter option type to full word format
        if option_type == "C":
            normalized_option_type = "call"
        else:
            normalized_option_type = "put"

        return ParsedInstrument(
            symbol=symbol,
            expiry_date=expiry_date,
            strike=strike,
            option_type=normalized_option_type,
            instrument_type="option",
            raw_ticker=ticker,
        )


class FutureParser:
    """Parses future instruments."""

    @staticmethod
    def parse(symbol: str, date_part: str, ticker: str) -> ParsedInstrument:
        """
        Parse future instrument.

        Args:
            symbol: Symbol (BTC/ETH)
            date_part: Date string
            ticker: Original ticker

        Returns:
            ParsedInstrument
        """
        expiry_date = DeribitDateParser.parse_date(date_part)

        return ParsedInstrument(
            symbol=symbol,
            expiry_date=expiry_date,
            strike=None,
            option_type=None,
            instrument_type="future",
            raw_ticker=ticker,
        )


class SpotParser:
    """Parses spot instruments."""

    @staticmethod
    def parse(base_symbol: str, quote_currency: str, ticker: str) -> ParsedInstrument:
        """
        Parse spot instrument.

        Args:
            base_symbol: Base symbol (BTC/ETH)
            quote_currency: Quote currency
            ticker: Original ticker

        Returns:
            ParsedInstrument
        """
        SymbolValidator.validate_quote_currency(quote_currency)

        # For spot pairs, we use a far future date as they don't expire
        # This satisfies code that expects a valid expiry_date field
        far_future = datetime(2099, 12, 31, 8, 0, 0, tzinfo=timezone.utc)

        return ParsedInstrument(
            symbol=base_symbol,
            expiry_date=far_future,
            strike=None,
            option_type=None,
            instrument_type="spot",
            raw_ticker=ticker,
        )
