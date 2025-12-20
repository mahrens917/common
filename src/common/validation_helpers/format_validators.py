"""Format validation helpers for currency codes and ticker symbols."""

from .exceptions import ValidationError


def _is_valid_t_separator(ticker: str, t_pos: int) -> bool:
    """Check if position is a valid T separator (followed by digit or dot)."""
    if t_pos >= len(ticker) - 1:
        return False
    suffix_after_t = ticker[t_pos + 1 :]
    return bool(suffix_after_t and (suffix_after_t[0].isdigit() or suffix_after_t[0] == "."))


def _find_potential_t_separators(ticker: str) -> list[int]:
    """Find all potential T separator positions in ticker."""
    if "T" not in ticker:
        raise ValidationError(f"Invalid ticker format - no 'T' found in ticker: {ticker}")
    t_positions = [i for i, char in enumerate(ticker) if char == "T"]
    return [t_pos for t_pos in t_positions if _is_valid_t_separator(ticker, t_pos)]


def _validate_separator_count(potential_separators: list[int], ticker: str) -> None:
    """Validate that exactly one T separator was found."""
    if len(potential_separators) > 1:
        raise ValidationError(
            f"Invalid ticker format - multiple 'T' separators found in ticker: {ticker}"
        )
    if len(potential_separators) == 0:
        raise ValidationError(
            f"Invalid ticker format - no valid 'T' separator found in ticker: {ticker}"
        )


def _find_ticker_t_separator(ticker: str) -> int:
    """Find the position of the 'T' separator in ticker."""
    potential_separators = _find_potential_t_separators(ticker)
    _validate_separator_count(potential_separators, ticker)
    return potential_separators[0]


def _validate_ticker_prefix(prefix: str, ticker: str) -> None:
    """Validate ticker prefix contains required components."""
    if len(prefix) == 0:
        raise ValidationError(f"Invalid ticker format - empty prefix before 'T': {ticker}")
    if "-" not in prefix:
        raise ValidationError(
            f"Invalid ticker format - missing date separator in prefix '{prefix}': {ticker}"
        )


def _validate_ticker_strike(strike_suffix: str, ticker: str) -> None:
    """Validate ticker strike suffix is numeric and valid."""
    from .numerical_validators import NumericalValidators

    if len(strike_suffix) == 0:
        raise ValidationError(f"Invalid ticker format - empty suffix after 'T': {ticker}")
    try:
        strike_price = float(strike_suffix)
        NumericalValidators.validate_strike_price(strike_price)
    except ValueError:
        raise ValidationError(
            f"Invalid ticker format - non-numeric strike price '{strike_suffix}' in ticker: {ticker}"
        )


class FormatValidators:
    """Validators for format compliance (currency codes, tickers)."""

    @staticmethod
    def validate_currency_code(currency: str) -> bool:
        """Validate currency code is supported."""
        try:
            stripped = currency.strip()
        except AttributeError:
            raise TypeError(f"currency must be string, got {type(currency).__name__}")
        if not stripped:
            raise ValidationError("Currency cannot be empty")
        supported_currencies = {"BTC", "ETH"}
        currency_upper = currency.upper()
        if currency_upper not in supported_currencies:
            raise ValidationError(
                f"Unsupported currency '{currency}', must be one of {supported_currencies}"
            )
        return True

    @staticmethod
    def validate_ticker_format(ticker: str) -> bool:
        """Validate Kalshi ticker format contains required components."""
        try:
            stripped = ticker.strip()
        except AttributeError:
            raise TypeError(f"ticker must be string, got {type(ticker).__name__}")
        if not stripped:
            raise ValidationError("Ticker cannot be empty")
        last_t_index = _find_ticker_t_separator(ticker)
        prefix = ticker[:last_t_index]
        strike_suffix = ticker[last_t_index + 1 :]
        _validate_ticker_prefix(prefix, ticker)
        _validate_ticker_strike(strike_suffix, ticker)
        return True
