"""Tests for Deribit market filters module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from common.market_filters.deribit import (
    DeribitFutureValidation,
    DeribitOptionValidation,
    validate_deribit_future,
    validate_deribit_option,
)


class TestDeribitOptionValidation:
    """Tests for DeribitOptionValidation dataclass."""

    def test_valid_option(self) -> None:
        """Creates valid option validation."""
        validation = DeribitOptionValidation(is_valid=True)

        assert validation.is_valid is True
        assert validation.reason is None

    def test_invalid_option_with_reason(self) -> None:
        """Creates invalid option validation with reason."""
        validation = DeribitOptionValidation(is_valid=False, reason="expired")

        assert validation.is_valid is False
        assert validation.reason == "expired"


class TestDeribitFutureValidation:
    """Tests for DeribitFutureValidation dataclass."""

    def test_valid_future(self) -> None:
        """Creates valid future validation."""
        validation = DeribitFutureValidation(is_valid=True)

        assert validation.is_valid is True
        assert validation.reason is None

    def test_invalid_future_with_reason(self) -> None:
        """Creates invalid future validation with reason."""
        validation = DeribitFutureValidation(is_valid=False, reason="missing_bid")

        assert validation.is_valid is False
        assert validation.reason == "missing_bid"


class TestValidateDeribitFuture:
    """Tests for validate_deribit_future function."""

    def test_valid_future(self) -> None:
        """Validates a valid future instrument."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) + timedelta(days=30)
        instrument.best_bid = 50000.0
        instrument.best_ask = 50100.0

        result = validate_deribit_future(instrument)

        assert result.is_valid is True
        assert result.reason is None

    def test_expired_future(self) -> None:
        """Rejects expired future."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) - timedelta(days=1)
        instrument.best_bid = 50000.0
        instrument.best_ask = 50100.0

        result = validate_deribit_future(instrument)

        assert result.is_valid is False
        assert result.reason == "expired"

    def test_missing_bid(self) -> None:
        """Rejects future with missing bid."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) + timedelta(days=30)
        instrument.best_bid = None
        instrument.best_ask = 50100.0

        result = validate_deribit_future(instrument)

        assert result.is_valid is False
        assert result.reason == "missing_bid"

    def test_missing_ask(self) -> None:
        """Rejects future with missing ask."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) + timedelta(days=30)
        instrument.best_bid = 50000.0
        instrument.best_ask = None

        result = validate_deribit_future(instrument)

        assert result.is_valid is False
        assert result.reason == "missing_ask"

    def test_invalid_bid_price(self) -> None:
        """Rejects future with zero or negative bid."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) + timedelta(days=30)
        instrument.best_bid = 0
        instrument.best_ask = 50100.0

        result = validate_deribit_future(instrument)

        assert result.is_valid is False
        assert result.reason == "invalid_price"

    def test_invalid_ask_price(self) -> None:
        """Rejects future with zero or negative ask."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) + timedelta(days=30)
        instrument.best_bid = 50000.0
        instrument.best_ask = 0

        result = validate_deribit_future(instrument)

        assert result.is_valid is False
        assert result.reason == "invalid_price"

    def test_invalid_spread_ask_below_bid(self) -> None:
        """Rejects future with ask below bid."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) + timedelta(days=30)
        instrument.best_bid = 50100.0
        instrument.best_ask = 50000.0

        result = validate_deribit_future(instrument)

        assert result.is_valid is False
        assert result.reason == "invalid_spread"

    def test_invalid_spread_ask_equal_bid(self) -> None:
        """Rejects future with ask equal to bid."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) + timedelta(days=30)
        instrument.best_bid = 50000.0
        instrument.best_ask = 50000.0

        result = validate_deribit_future(instrument)

        assert result.is_valid is False
        assert result.reason == "invalid_spread"

    def test_uses_custom_now_parameter(self) -> None:
        """Respects custom now parameter for expiry check."""
        instrument = MagicMock()
        past_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        instrument.expiry = datetime(2024, 6, 1, tzinfo=timezone.utc)
        instrument.best_bid = 50000.0
        instrument.best_ask = 50100.0

        result = validate_deribit_future(instrument, now=past_time)

        assert result.is_valid is True


class TestValidateDeribitOption:
    """Tests for validate_deribit_option function."""

    def test_expired_option(self) -> None:
        """Rejects expired option."""
        instrument = MagicMock()
        instrument.expiry = datetime.now(timezone.utc) - timedelta(days=1)
        instrument.best_bid = 0.05
        instrument.best_ask = 0.06
        instrument.best_bid_size = 1.0
        instrument.best_ask_size = 1.0
        instrument.timestamp = datetime.now(timezone.utc).timestamp() * 1000

        result = validate_deribit_option(instrument)

        assert result.is_valid is False
        assert result.reason == "expired"

    def test_uses_custom_now_parameter(self) -> None:
        """Respects custom now parameter for expiry check."""
        instrument = MagicMock()
        past_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        instrument.expiry = datetime(2024, 6, 1, tzinfo=timezone.utc)
        instrument.best_bid = 0.05
        instrument.best_ask = 0.06
        instrument.best_bid_size = 1.0
        instrument.best_ask_size = 1.0
        instrument.timestamp = past_time.timestamp() * 1000

        result = validate_deribit_option(instrument, now=past_time)

        assert result.is_valid is True
