"""Unit tests for MicroPriceCalculator class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from common.data_models.micro_price_helpers.calculations import MicroPriceCalculator


class TestComputeIntrinsicValue:
    """Tests for compute_intrinsic_value method."""

    def test_call_option_in_the_money(self) -> None:
        """Test call option with spot > strike (ITM)."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="call", strike=100.0, spot_price=110.0)
        assert result == 10.0

    def test_call_option_at_the_money(self) -> None:
        """Test call option with spot = strike (ATM)."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="call", strike=100.0, spot_price=100.0)
        assert result == 0.0

    def test_call_option_out_of_the_money(self) -> None:
        """Test call option with spot < strike (OTM)."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="call", strike=100.0, spot_price=90.0)
        assert result == 0.0

    def test_put_option_in_the_money(self) -> None:
        """Test put option with strike > spot (ITM)."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="put", strike=100.0, spot_price=90.0)
        assert result == 10.0

    def test_put_option_at_the_money(self) -> None:
        """Test put option with strike = spot (ATM)."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="put", strike=100.0, spot_price=100.0)
        assert result == 0.0

    def test_put_option_out_of_the_money(self) -> None:
        """Test put option with strike < spot (OTM)."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="put", strike=100.0, spot_price=110.0)
        assert result == 0.0

    def test_case_insensitive_call(self) -> None:
        """Test that 'CALL' is handled case-insensitively."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="CALL", strike=100.0, spot_price=110.0)
        assert result == 10.0

    def test_case_insensitive_put(self) -> None:
        """Test that 'PUT' is handled case-insensitively."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="PUT", strike=100.0, spot_price=90.0)
        assert result == 10.0

    def test_mixed_case_call(self) -> None:
        """Test that 'Call' is handled case-insensitively."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="Call", strike=100.0, spot_price=105.0)
        assert result == 5.0

    def test_deep_in_the_money_call(self) -> None:
        """Test deep ITM call option."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="call", strike=100.0, spot_price=200.0)
        assert result == 100.0

    def test_deep_in_the_money_put(self) -> None:
        """Test deep ITM put option."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="put", strike=200.0, spot_price=100.0)
        assert result == 100.0

    def test_small_intrinsic_value(self) -> None:
        """Test small intrinsic values."""
        result = MicroPriceCalculator.compute_intrinsic_value(option_type="call", strike=100.0, spot_price=100.01)
        assert result == pytest.approx(0.01)


class TestComputeTimeValue:
    """Tests for compute_time_value method."""

    def test_time_value_for_otm_option(self) -> None:
        """Test time value when option is OTM (micro_price = time_value)."""
        result = MicroPriceCalculator.compute_time_value(option_type="call", strike=100.0, spot_price=90.0, micro_price=5.0)
        # Intrinsic = 0, so time value = micro_price
        assert result == 5.0

    def test_time_value_for_itm_option(self) -> None:
        """Test time value when option is ITM."""
        result = MicroPriceCalculator.compute_time_value(option_type="call", strike=100.0, spot_price=110.0, micro_price=15.0)
        # Intrinsic = 10, so time value = 15 - 10 = 5
        assert result == 5.0

    def test_time_value_for_atm_option(self) -> None:
        """Test time value when option is ATM."""
        result = MicroPriceCalculator.compute_time_value(option_type="call", strike=100.0, spot_price=100.0, micro_price=3.0)
        # Intrinsic = 0, so time value = micro_price
        assert result == 3.0

    def test_zero_time_value(self) -> None:
        """Test when micro_price equals intrinsic value (zero time value)."""
        result = MicroPriceCalculator.compute_time_value(option_type="call", strike=100.0, spot_price=110.0, micro_price=10.0)
        # Intrinsic = 10, micro_price = 10, so time value = 0
        assert result == 0.0

    def test_negative_time_value_clamped_to_zero(self) -> None:
        """Test that negative time values are clamped to zero."""
        result = MicroPriceCalculator.compute_time_value(option_type="call", strike=100.0, spot_price=110.0, micro_price=5.0)
        # Intrinsic = 10, micro_price = 5, would be -5 but clamped to 0
        assert result == 0.0

    def test_put_option_time_value(self) -> None:
        """Test time value calculation for put option."""
        result = MicroPriceCalculator.compute_time_value(option_type="put", strike=100.0, spot_price=90.0, micro_price=15.0)
        # Intrinsic = 10, so time value = 15 - 10 = 5
        assert result == 5.0

    def test_all_time_value_no_intrinsic(self) -> None:
        """Test when option has only time value, no intrinsic value."""
        result = MicroPriceCalculator.compute_time_value(option_type="put", strike=100.0, spot_price=110.0, micro_price=2.5)
        # Intrinsic = 0, so time value = 2.5
        assert result == 2.5


class TestComputeMicroPriceMetrics:
    """Tests for compute_micro_price_metrics method."""

    @patch("common.data_models.micro_price_helpers.calculations.MetricsCalculator.compute_micro_price_metrics")
    def test_delegates_to_metrics_calculator(self, mock_compute: MagicMock) -> None:
        """Test that method delegates to MetricsCalculator."""
        mock_compute.return_value = (1.0, 0.5, 50.0, 0.4, 0.6, 0.02)

        result = MicroPriceCalculator.compute_micro_price_metrics(best_bid=49.0, best_ask=51.0, bid_size=100.0, ask_size=200.0)

        mock_compute.assert_called_once_with(bid_price=49.0, ask_price=51.0, bid_size=100.0, ask_size=200.0, symbol="UNKNOWN")

    @patch("common.data_models.micro_price_helpers.calculations.MetricsCalculator.compute_micro_price_metrics")
    def test_reorders_return_values(self, mock_compute: MagicMock) -> None:
        """Test that return values are reordered correctly."""
        # MetricsCalculator returns: (s_raw, i_raw, p_raw, g, h, relative_spread)
        mock_compute.return_value = (2.0, 0.6, 51.0, 0.45, 0.55, 0.039)

        result = MicroPriceCalculator.compute_micro_price_metrics(best_bid=50.0, best_ask=52.0, bid_size=150.0, ask_size=100.0)

        # Should return: (s_raw, relative_spread, i_raw, p_raw, g, h)
        assert result == (2.0, 0.039, 0.6, 51.0, 0.45, 0.55)

    @patch("common.data_models.micro_price_helpers.calculations.MetricsCalculator.compute_micro_price_metrics")
    def test_passes_symbol_unknown(self, mock_compute: MagicMock) -> None:
        """Test that symbol 'UNKNOWN' is passed to MetricsCalculator."""
        mock_compute.return_value = (1.0, 0.5, 50.0, 0.4, 0.6, 0.02)

        MicroPriceCalculator.compute_micro_price_metrics(best_bid=49.0, best_ask=51.0, bid_size=100.0, ask_size=200.0)

        call_kwargs = mock_compute.call_args[1]
        assert call_kwargs["symbol"] == "UNKNOWN"

    @patch("common.data_models.micro_price_helpers.calculations.MetricsCalculator.compute_micro_price_metrics")
    def test_maps_parameter_names(self, mock_compute: MagicMock) -> None:
        """Test that parameter names are correctly mapped."""
        mock_compute.return_value = (1.0, 0.5, 50.0, 0.4, 0.6, 0.02)

        MicroPriceCalculator.compute_micro_price_metrics(best_bid=48.0, best_ask=52.0, bid_size=120.0, ask_size=80.0)

        call_kwargs = mock_compute.call_args[1]
        assert call_kwargs["bid_price"] == 48.0
        assert call_kwargs["ask_price"] == 52.0
        assert call_kwargs["bid_size"] == 120.0
        assert call_kwargs["ask_size"] == 80.0

    @patch("common.data_models.micro_price_helpers.calculations.MetricsCalculator.compute_micro_price_metrics")
    def test_returns_six_element_tuple(self, mock_compute: MagicMock) -> None:
        """Test that return value is a 6-element tuple."""
        mock_compute.return_value = (1.5, 0.55, 50.5, 0.42, 0.58, 0.029)

        result = MicroPriceCalculator.compute_micro_price_metrics(best_bid=50.0, best_ask=51.5, bid_size=100.0, ask_size=100.0)

        assert isinstance(result, tuple)
        assert len(result) == 6

    @patch("common.data_models.micro_price_helpers.calculations.MetricsCalculator.compute_micro_price_metrics")
    def test_handles_equal_bid_ask_sizes(self, mock_compute: MagicMock) -> None:
        """Test with equal bid and ask sizes."""
        mock_compute.return_value = (1.0, 0.5, 50.0, 0.5, 0.5, 0.02)

        result = MicroPriceCalculator.compute_micro_price_metrics(best_bid=49.0, best_ask=51.0, bid_size=100.0, ask_size=100.0)

        # When sizes are equal, i_raw should be 0.5, g and h should be 0.5
        assert result[2] == 0.5  # i_raw
        assert result[4] == 0.5  # g
        assert result[5] == 0.5  # h

    @patch("common.data_models.micro_price_helpers.calculations.MetricsCalculator.compute_micro_price_metrics")
    def test_handles_large_spread(self, mock_compute: MagicMock) -> None:
        """Test with large spread between bid and ask."""
        mock_compute.return_value = (10.0, 0.6, 55.0, 0.4, 0.6, 0.182)

        result = MicroPriceCalculator.compute_micro_price_metrics(best_bid=50.0, best_ask=60.0, bid_size=100.0, ask_size=200.0)

        # absolute_spread (s_raw)
        assert result[0] == 10.0
        # relative_spread
        assert result[1] == pytest.approx(0.182)
