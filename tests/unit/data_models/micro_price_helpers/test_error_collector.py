"""Tests for error collector module."""

from src.common.data_models.micro_price_helpers.error_collector import (
    ErrorCollector,
)
from src.common.data_models.micro_price_helpers.validation_params import (
    ValidationErrorParams,
)


class TestErrorCollectorSpreadErrors:
    """Tests for ErrorCollector.collect_spread_errors."""

    def test_no_errors_for_positive_spread(self) -> None:
        """Returns empty list for positive spread."""
        errors = ErrorCollector.collect_spread_errors(0.05)

        assert errors == []

    def test_no_errors_for_zero_spread(self) -> None:
        """Returns empty list for zero spread."""
        errors = ErrorCollector.collect_spread_errors(0.0)

        assert errors == []

    def test_error_for_negative_spread(self) -> None:
        """Returns error for negative spread."""
        errors = ErrorCollector.collect_spread_errors(-0.01)

        assert len(errors) == 1
        assert "Spread constraint violated" in errors[0]
        assert "-0.01" in errors[0]


class TestErrorCollectorIntensityErrors:
    """Tests for ErrorCollector.collect_intensity_errors."""

    def test_no_errors_for_valid_intensity(self) -> None:
        """Returns empty list for intensity in [0, 1]."""
        errors = ErrorCollector.collect_intensity_errors(0.5)

        assert errors == []

    def test_no_errors_for_zero_intensity(self) -> None:
        """Returns empty list for zero intensity."""
        errors = ErrorCollector.collect_intensity_errors(0.0)

        assert errors == []

    def test_no_errors_for_one_intensity(self) -> None:
        """Returns empty list for intensity of 1."""
        errors = ErrorCollector.collect_intensity_errors(1.0)

        assert errors == []

    def test_error_for_negative_intensity(self) -> None:
        """Returns error for negative intensity."""
        errors = ErrorCollector.collect_intensity_errors(-0.1)

        assert len(errors) == 1
        assert "Intensity constraint violated" in errors[0]

    def test_error_for_intensity_greater_than_one(self) -> None:
        """Returns error for intensity > 1."""
        errors = ErrorCollector.collect_intensity_errors(1.1)

        assert len(errors) == 1
        assert "Intensity constraint violated" in errors[0]


class TestErrorCollectorMicroPriceErrors:
    """Tests for ErrorCollector.collect_micro_price_errors."""

    def test_no_errors_for_price_within_bounds(self) -> None:
        """Returns empty list when price is within bid-ask bounds."""
        errors = ErrorCollector.collect_micro_price_errors(0.05, 0.10, 0.07)

        assert errors == []

    def test_no_errors_for_price_at_bid(self) -> None:
        """Returns empty list when price equals bid."""
        errors = ErrorCollector.collect_micro_price_errors(0.05, 0.10, 0.05)

        assert errors == []

    def test_no_errors_for_price_at_ask(self) -> None:
        """Returns empty list when price equals ask."""
        errors = ErrorCollector.collect_micro_price_errors(0.05, 0.10, 0.10)

        assert errors == []

    def test_error_for_price_below_bid(self) -> None:
        """Returns error when price is below bid."""
        errors = ErrorCollector.collect_micro_price_errors(0.05, 0.10, 0.03)

        assert len(errors) == 1
        assert "Micro price constraint violated" in errors[0]

    def test_error_for_price_above_ask(self) -> None:
        """Returns error when price is above ask."""
        errors = ErrorCollector.collect_micro_price_errors(0.05, 0.10, 0.12)

        assert len(errors) == 1
        assert "Micro price constraint violated" in errors[0]


class TestErrorCollectorReconstructionErrors:
    """Tests for ErrorCollector.collect_reconstruction_errors."""

    def test_no_errors_for_valid_reconstruction(self) -> None:
        """Returns empty list when reconstruction is valid."""
        # p_raw - i_raw * spread = bid
        # 0.075 - 0.5 * 0.05 = 0.05 ✓
        # p_raw + (1-i_raw) * spread = ask
        # 0.075 + 0.5 * 0.05 = 0.10 ✓
        errors = ErrorCollector.collect_reconstruction_errors(
            best_bid=0.05,
            best_ask=0.10,
            p_raw=0.075,
            i_raw=0.5,
            absolute_spread=0.05,
        )

        assert errors == []

    def test_error_for_bid_reconstruction_mismatch(self) -> None:
        """Returns error when bid reconstruction fails."""
        errors = ErrorCollector.collect_reconstruction_errors(
            best_bid=0.05,
            best_ask=0.10,
            p_raw=0.08,
            i_raw=0.5,
            absolute_spread=0.05,
        )

        assert len(errors) >= 1
        assert any("Bid reconstruction" in e or "Ask reconstruction" in e for e in errors)


class TestErrorCollectorBasicDataErrors:
    """Tests for ErrorCollector.collect_basic_data_errors."""

    def test_no_errors_for_valid_data(self) -> None:
        """Returns empty list for valid data."""
        errors = ErrorCollector.collect_basic_data_errors(10.0, 20.0, "call")

        assert errors == []

    def test_no_errors_for_put_option(self) -> None:
        """Returns empty list for put option."""
        errors = ErrorCollector.collect_basic_data_errors(10.0, 20.0, "put")

        assert errors == []

    def test_error_for_negative_bid_size(self) -> None:
        """Returns error for negative bid size."""
        errors = ErrorCollector.collect_basic_data_errors(-10.0, 20.0, "call")

        assert len(errors) == 1
        assert "Bid size cannot be negative" in errors[0]

    def test_error_for_negative_ask_size(self) -> None:
        """Returns error for negative ask size."""
        errors = ErrorCollector.collect_basic_data_errors(10.0, -20.0, "call")

        assert len(errors) == 1
        assert "Ask size cannot be negative" in errors[0]

    def test_error_for_invalid_option_type(self) -> None:
        """Returns error for invalid option type."""
        errors = ErrorCollector.collect_basic_data_errors(10.0, 20.0, "straddle")

        assert len(errors) == 1
        assert "Option type must be 'call' or 'put'" in errors[0]

    def test_multiple_errors(self) -> None:
        """Returns multiple errors when multiple constraints violated."""
        errors = ErrorCollector.collect_basic_data_errors(-10.0, -20.0, "straddle")

        assert len(errors) == 3


class TestErrorCollectorGetValidationErrors:
    """Tests for ErrorCollector.get_validation_errors."""

    def test_returns_empty_list_for_valid_params(self) -> None:
        """Returns empty list for valid parameters."""
        params = ValidationErrorParams(
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
            absolute_spread=0.05,
            i_raw=0.5,
            p_raw=0.075,
        )

        errors = ErrorCollector.get_validation_errors(params)

        assert errors == []

    def test_returns_errors_for_invalid_params(self) -> None:
        """Returns errors for invalid parameters."""
        params = ValidationErrorParams(
            best_bid=0.05,
            best_ask=0.10,
            best_bid_size=-10.0,
            best_ask_size=20.0,
            option_type="call",
            absolute_spread=-0.05,
            i_raw=1.5,
            p_raw=0.15,
        )

        errors = ErrorCollector.get_validation_errors(params)

        assert len(errors) > 0
