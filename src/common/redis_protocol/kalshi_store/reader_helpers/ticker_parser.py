"""
Ticker Parser - Parse and validate Kalshi market tickers

Handles ticker parsing, normalization, and currency matching logic.
"""

from typing import Any


class TickerParser:
    """Parse and validate Kalshi market ticker formats"""

    @staticmethod
    def normalize_ticker(market_ticker: Any) -> str:
        """
        Normalize a market ticker to string format

        Args:
            market_ticker: Ticker as bytes, str, or other type

        Returns:
            Normalized ticker string
        """
        if isinstance(market_ticker, bytes):
            return market_ticker.decode("utf-8")
        return str(market_ticker)

    @staticmethod
    def is_market_for_currency(market_ticker: str, currency: str) -> bool:
        """
        Check if a market ticker belongs to the specified currency.

        Uses precise matching to avoid cross-currency contamination.
        Updated to handle actual Kalshi ticker patterns found in Redis:
        - KXBTC*, KXBTCD* for BTC markets
        - KXETH*, KXETHD* for ETH markets

        Args:
            market_ticker: The market ticker to check
            currency: The currency to match against (BTC or ETH)

        Returns:
            True if the market belongs to the currency, False otherwise
        """
        if not market_ticker or not currency:
            return False

        ticker_upper = market_ticker.upper()
        currency_upper = currency.upper()

        return ticker_upper.startswith(f"KX{currency_upper}")

    @staticmethod
    def iter_currency_markets(markets: Any, currency: str):
        """
        Filter markets by currency from an iterable

        Args:
            markets: Iterable of market tickers (bytes or str)
            currency: Currency to filter by

        Yields:
            Market tickers matching the currency
        """
        target = currency.upper()
        for market in markets:
            market_str = market.decode("utf-8") if isinstance(market, bytes) else str(market)
            if target in market_str:
                yield market_str
