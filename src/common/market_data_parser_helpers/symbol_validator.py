"""Symbol validation helpers for Deribit instruments."""

from typing import Any, Optional

from ..market_data_parser import ParsingError, ValidationError

# Constants
_CONST_2 = 2


class SymbolValidator:
    """Validates instrument symbols."""

    # Supported symbols
    VALID_SYMBOLS = {"BTC", "ETH"}
    VALID_QUOTE_CURRENCIES = {"USD", "USDC", "USDT", "EUR"}

    @classmethod
    def validate_symbol(cls, symbol: str, strict_symbol: Optional[str] = None) -> None:
        """
        Validate symbol.

        Args:
            symbol: Symbol to validate
            strict_symbol: If provided, validates symbol matches this

        Raises:
            ParsingError: If symbol is invalid
            ValidationError: If symbol doesn't match strict_symbol
        """
        if symbol not in cls.VALID_SYMBOLS:
            raise ParsingError(f"Unsupported symbol: {symbol}")

        if strict_symbol and symbol != strict_symbol:
            raise ValidationError(f"Symbol mismatch: expected {strict_symbol}, got {symbol}")

    @classmethod
    def validate_quote_currency(cls, quote_currency: str) -> None:
        """
        Validate quote currency for spot pairs.

        Args:
            quote_currency: Quote currency to validate

        Raises:
            ParsingError: If quote currency is invalid
        """
        if quote_currency not in cls.VALID_QUOTE_CURRENCIES:
            raise ParsingError(f"Unsupported quote currency: {quote_currency}")

    @classmethod
    def extract_symbol_from_ticker(cls, ticker: Any) -> Optional[str]:
        """
        Extract symbol from ticker without full validation.

        Returns:
            Symbol or None if extraction fails
        """
        if not ticker or not isinstance(ticker, str):
            return None

        parts = ticker.strip().upper().split("-")
        if len(parts) >= _CONST_2:
            symbol = parts[0]
            return symbol if symbol in cls.VALID_SYMBOLS else None

        return None
