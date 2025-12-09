"""Pattern matching helpers for Deribit instrument tickers."""

import re
from typing import Optional, Tuple


class TickerPatternMatcher:
    """Matches Deribit ticker patterns."""

    # Regex patterns for validation
    OPTION_PATTERN = re.compile(r"^([A-Z]{3})-(\d{1,2}[A-Z]{3}\d{2})-(\d+)-([CP])$")
    FUTURE_PATTERN = re.compile(r"^([A-Z]{3})-(\d{1,2}[A-Z]{3}\d{2})$")
    SPOT_PATTERN = re.compile(r"^([A-Z]{3})_([A-Z]{3,4})$")

    @classmethod
    def match_option(cls, ticker: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Match option pattern.

        Args:
            ticker: Deribit ticker

        Returns:
            (symbol, date_part, strike_str, option_type) or None if no match
        """
        match = cls.OPTION_PATTERN.match(ticker)
        if match:
            symbol, date_part, strike_str, option_type = match.groups()
            return symbol, date_part, strike_str, option_type
        return None

    @classmethod
    def match_future(cls, ticker: str) -> Optional[Tuple[str, str]]:
        """
        Match future pattern.

        Args:
            ticker: Deribit ticker

        Returns:
            (symbol, date_part) or None if no match
        """
        match = cls.FUTURE_PATTERN.match(ticker)
        if match:
            symbol, date_part = match.groups()
            return symbol, date_part
        return None

    @classmethod
    def match_spot(cls, ticker: str) -> Optional[Tuple[str, str]]:
        """
        Match spot pattern.

        Args:
            ticker: Deribit ticker

        Returns:
            (base_symbol, quote_currency) or None if no match
        """
        match = cls.SPOT_PATTERN.match(ticker)
        if match:
            base_symbol, quote_currency = match.groups()
            return base_symbol, quote_currency
        return None
