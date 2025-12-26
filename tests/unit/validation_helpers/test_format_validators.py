"""Tests for format_validators module."""

import pytest

from common.validation_helpers.exceptions import ValidationError
from common.validation_helpers.format_validators import (
    FormatValidators,
    _find_potential_t_separators,
    _find_ticker_t_separator,
    _is_valid_t_separator,
    _validate_separator_count,
    _validate_ticker_prefix,
    _validate_ticker_strike,
)


class TestIsValidTSeparator:
    """Tests for _is_valid_t_separator function."""

    def test_valid_t_followed_by_digit(self) -> None:
        """Test T followed by digit is valid."""
        assert _is_valid_t_separator("KXBTC-24DEC25-T45", 14) is True

    def test_valid_t_followed_by_dot(self) -> None:
        """Test T followed by dot is valid."""
        assert _is_valid_t_separator("KXBTC-24DEC25-T.5", 14) is True

    def test_t_at_end_of_string(self) -> None:
        """Test T at end is invalid."""
        assert _is_valid_t_separator("KXBTCT", 5) is False

    def test_t_followed_by_letter(self) -> None:
        """Test T followed by letter is invalid."""
        assert _is_valid_t_separator("KXBTC-24DEC25-TA", 14) is False


class TestFindPotentialTSeparators:
    """Tests for _find_potential_t_separators function."""

    def test_finds_valid_t_separator(self) -> None:
        """Test finding valid T separator."""
        result = _find_potential_t_separators("KXBTC-24DEC25-T45")
        assert result == [14]

    def test_no_t_in_ticker(self) -> None:
        """Test raises error when no T in ticker."""
        with pytest.raises(ValidationError, match="no 'T' found"):
            _find_potential_t_separators("KXBC-24DEC25-45")

    def test_multiple_potential_separators(self) -> None:
        """Test finds multiple potential separators."""
        result = _find_potential_t_separators("T1-T2")
        assert len(result) == 2


class TestValidateSeparatorCount:
    """Tests for _validate_separator_count function."""

    def test_exactly_one_separator(self) -> None:
        """Test exactly one separator is valid."""
        _validate_separator_count([14], "TICKER")

    def test_multiple_separators_raises(self) -> None:
        """Test multiple separators raises error."""
        with pytest.raises(ValidationError, match="multiple 'T' separators"):
            _validate_separator_count([10, 15], "TICKER")

    def test_no_separators_raises(self) -> None:
        """Test no separators raises error."""
        with pytest.raises(ValidationError, match="no valid 'T' separator"):
            _validate_separator_count([], "TICKER")


class TestFindTickerTSeparator:
    """Tests for _find_ticker_t_separator function."""

    def test_finds_separator_position(self) -> None:
        """Test finds separator position."""
        result = _find_ticker_t_separator("KXBTC-24DEC25-T45")
        assert result == 14


class TestValidateTickerPrefix:
    """Tests for _validate_ticker_prefix function."""

    def test_valid_prefix(self) -> None:
        """Test valid prefix passes."""
        _validate_ticker_prefix("KXBTC-24DEC25", "TICKER")

    def test_empty_prefix_raises(self) -> None:
        """Test empty prefix raises error."""
        with pytest.raises(ValidationError, match="empty prefix"):
            _validate_ticker_prefix("", "TICKER")

    def test_missing_date_separator_raises(self) -> None:
        """Test missing date separator raises error."""
        with pytest.raises(ValidationError, match="missing date separator"):
            _validate_ticker_prefix("KXBTC24DEC25", "TICKER")


class TestValidateTickerStrike:
    """Tests for _validate_ticker_strike function."""

    def test_valid_strike(self) -> None:
        """Test valid numeric strike passes."""
        _validate_ticker_strike("45", "TICKER")

    def test_valid_decimal_strike(self) -> None:
        """Test valid decimal strike passes."""
        _validate_ticker_strike("45.5", "TICKER")

    def test_empty_strike_raises(self) -> None:
        """Test empty strike raises error."""
        with pytest.raises(ValidationError, match="empty suffix"):
            _validate_ticker_strike("", "TICKER")

    def test_non_numeric_strike_raises(self) -> None:
        """Test non-numeric strike raises error."""
        with pytest.raises(ValidationError, match="non-numeric strike"):
            _validate_ticker_strike("ABC", "TICKER")


class TestFormatValidators:
    """Tests for FormatValidators class."""

    def test_validate_currency_code_btc(self) -> None:
        """Test BTC is valid currency."""
        assert FormatValidators.validate_currency_code("BTC") is True

    def test_validate_currency_code_eth(self) -> None:
        """Test ETH is valid currency."""
        assert FormatValidators.validate_currency_code("ETH") is True

    def test_validate_currency_code_lowercase(self) -> None:
        """Test lowercase is valid."""
        assert FormatValidators.validate_currency_code("btc") is True

    def test_validate_currency_code_empty(self) -> None:
        """Test empty currency raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            FormatValidators.validate_currency_code("")

    def test_validate_currency_code_unsupported(self) -> None:
        """Test unsupported currency raises error."""
        with pytest.raises(ValidationError, match="Unsupported currency"):
            FormatValidators.validate_currency_code("XRP")

    def test_validate_currency_code_non_string(self) -> None:
        """Test non-string raises TypeError."""
        with pytest.raises(TypeError, match="must be string"):
            FormatValidators.validate_currency_code(123)

    def test_validate_ticker_format_valid(self) -> None:
        """Test valid ticker format passes."""
        assert FormatValidators.validate_ticker_format("KXBTC-24DEC25-T45") is True

    def test_validate_ticker_format_with_decimal(self) -> None:
        """Test ticker with decimal strike passes."""
        assert FormatValidators.validate_ticker_format("KXETH-24DEC25-T2.5") is True

    def test_validate_ticker_format_empty(self) -> None:
        """Test empty ticker raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            FormatValidators.validate_ticker_format("")

    def test_validate_ticker_format_non_string(self) -> None:
        """Test non-string ticker raises TypeError."""
        with pytest.raises(TypeError, match="must be string"):
            FormatValidators.validate_ticker_format(123)
