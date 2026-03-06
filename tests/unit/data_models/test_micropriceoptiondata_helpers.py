"""Unit tests for micropriceoptiondata_helpers modules."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from common.data_models.micropriceoptiondata_helpers.properties import MicroPriceProperties


class TestMicroPriceProperties:
    """Tests for MicroPriceProperties."""

    def test_get_is_future(self) -> None:
        assert MicroPriceProperties.get_is_future() is False

    def test_get_expiry_timestamp(self) -> None:
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = MicroPriceProperties.get_expiry_timestamp(dt)
        assert isinstance(result, int)
        assert result == int(dt.timestamp())

    def test_get_bid_price(self) -> None:
        assert MicroPriceProperties.get_bid_price(42.5) == 42.5

    def test_get_ask_price(self) -> None:
        assert MicroPriceProperties.get_ask_price(43.0) == 43.0

    def test_get_mid_price(self) -> None:
        assert MicroPriceProperties.get_mid_price(10.0, 20.0) == 15.0

    def test_get_spread(self) -> None:
        assert MicroPriceProperties.get_spread(5.0) == 5.0

    def test_check_is_call_true(self) -> None:
        assert MicroPriceProperties.check_is_call("call") is True

    def test_check_is_call_false(self) -> None:
        assert MicroPriceProperties.check_is_call("put") is False

    def test_check_is_put_true(self) -> None:
        assert MicroPriceProperties.check_is_put("put") is True

    def test_check_is_put_false(self) -> None:
        assert MicroPriceProperties.check_is_put("call") is False

    def test_check_is_call_case_insensitive(self) -> None:
        assert MicroPriceProperties.check_is_call("CALL") is True

    def test_check_is_put_case_insensitive(self) -> None:
        assert MicroPriceProperties.check_is_put("PUT") is True


class TestFromEnhancedOptionDataFactory:
    """Tests for factory.from_enhanced_option_data."""

    def test_creates_instance_from_enhanced_option(self) -> None:
        from common.data_models.micropriceoptiondata_helpers.factory import from_enhanced_option_data

        dt = datetime(2025, 6, 1, tzinfo=timezone.utc)

        mock_enhanced = MagicMock()
        mock_enhanced.strike = 100.0

        with (
            patch("common.data_models.micropriceoptiondata_helpers.factory.MicroPriceConversionHelpers") as mock_helpers,
            patch("common.data_models.micropriceoptiondata_helpers.factory.MicroPriceCalculator") as mock_calc,
        ):
            mock_helpers.resolve_instrument_name.return_value = "BTC-25JUN25-100-C"
            mock_helpers.determine_underlying.return_value = "BTC"
            mock_helpers.determine_expiry.return_value = dt
            mock_helpers.resolve_option_type.return_value = "call"
            mock_helpers.extract_prices.return_value = (0.5, 1.0)
            mock_helpers.extract_sizes.return_value = (10.0, 20.0)
            mock_helpers.resolve_timestamp.return_value = 1234567890

            mock_calc.compute_micro_price_metrics.return_value = (0.5, 0.333, 0.667, -0.693, -0.405, 0.75)

            mock_cls = MagicMock()
            mock_cls.return_value = "created_instance"

            result = from_enhanced_option_data(mock_enhanced, mock_cls)

        assert result == "created_instance"
        mock_cls.assert_called_once_with(
            instrument_name="BTC-25JUN25-100-C",
            underlying="BTC",
            strike=100.0,
            expiry=dt,
            option_type="call",
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=10.0,
            best_ask_size=20.0,
            timestamp=1234567890,
            absolute_spread=0.5,
            relative_spread=0.333,
            i_raw=0.667,
            p_raw=-0.693,
            g=-0.405,
            h=0.75,
        )
