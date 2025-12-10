"""Tests for micro price errors module."""

from common.data_models.micro_price_helpers.errors import (
    OptionDataConversionError,
)


class TestOptionDataConversionError:
    """Tests for OptionDataConversionError exception class."""

    def test_is_value_error(self) -> None:
        """Is a subclass of ValueError."""
        error = OptionDataConversionError("test message")

        assert isinstance(error, ValueError)

    def test_has_message(self) -> None:
        """Has the provided message."""
        error = OptionDataConversionError("test message")

        assert str(error) == "test message"

    def test_can_be_raised_and_caught(self) -> None:
        """Can be raised and caught as ValueError."""
        try:
            raise OptionDataConversionError("conversion failed")
        except ValueError as e:
            assert str(e) == "conversion failed"
