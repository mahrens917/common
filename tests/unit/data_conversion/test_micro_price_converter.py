"""Tests for micro price converter module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from src.common.data_conversion.micro_price_converter import MicroPriceConverter


class TestMicroPriceConverterConvertSingle:
    """Tests for MicroPriceConverter.convert_instrument_to_micro_price_option_data."""

    def test_convert_instrument_calls_helpers(self) -> None:
        """Verifies the conversion calls the helper modules."""
        # Create mock instrument with required attributes
        mock_instrument = MagicMock()
        mock_instrument.strike = "50000"
        mock_instrument.option_type = "call"
        mock_instrument.expiry = datetime(2025, 1, 1)

        # Patch the helper modules at their source location (the package __init__)
        with patch(
            "src.common.data_conversion.micro_price_helpers.FieldValidator"
        ) as mock_validator_cls:
            with patch(
                "src.common.data_conversion.micro_price_helpers.FieldResolver"
            ) as mock_resolver_cls:
                with patch(
                    "src.common.data_conversion.micro_price_helpers.MetricsCalculator"
                ) as mock_calculator_cls:
                    with patch(
                        "src.common.data_conversion.micro_price_converter.MicroPriceOptionData"
                    ) as mock_data_cls:
                        # Setup mocks
                        mock_validator_cls.extract_prices_and_sizes.return_value = (
                            100.0,
                            101.0,
                            10.0,
                            15.0,
                        )
                        mock_resolver_cls.resolve_expiry_datetime.return_value = datetime(
                            2025, 1, 1
                        )
                        mock_resolver_cls.resolve_instrument_name.return_value = (
                            "BTC-25JAN01-50000-C"
                        )
                        mock_resolver_cls.resolve_quote_timestamp.return_value = datetime(
                            2024, 12, 1, 12, 0
                        )
                        mock_calculator_cls.compute_micro_price_metrics.return_value = (
                            1.0,
                            100.4,
                            100.6,
                            0.1,
                            0.2,
                            0.01,
                        )
                        mock_data_cls.return_value = MagicMock()

                        result = MicroPriceConverter.convert_instrument_to_micro_price_option_data(
                            mock_instrument, "BTC"
                        )

                        mock_validator_cls.validate_required_fields.assert_called_once()
                        mock_validator_cls.extract_prices_and_sizes.assert_called_once()
                        assert result is not None


class TestMicroPriceConverterConvertList:
    """Tests for MicroPriceConverter.convert_instruments_to_micro_price_data."""

    def test_convert_instruments_list_delegates_to_batch(self) -> None:
        """Converts list of instruments using batch converter."""
        mock_instruments = [MagicMock(), MagicMock()]
        mock_result = [MagicMock(), MagicMock()]

        with patch(
            "src.common.data_conversion.micro_price_helpers.BatchConverter"
        ) as mock_batch_cls:
            mock_batch_cls.convert_instruments_to_micro_price_data.return_value = mock_result

            result = MicroPriceConverter.convert_instruments_to_micro_price_data(
                mock_instruments, "BTC"
            )

            mock_batch_cls.convert_instruments_to_micro_price_data.assert_called_once()
            assert result is mock_result

    def test_convert_instruments_uses_default_currency(self) -> None:
        """Uses default currency when not specified."""
        mock_instruments = [MagicMock()]
        mock_result = [MagicMock()]

        with patch(
            "src.common.data_conversion.micro_price_helpers.BatchConverter"
        ) as mock_batch_cls:
            mock_batch_cls.convert_instruments_to_micro_price_data.return_value = mock_result

            result = MicroPriceConverter.convert_instruments_to_micro_price_data(mock_instruments)

            call_args = mock_batch_cls.convert_instruments_to_micro_price_data.call_args
            assert call_args[0][1] == "BTC"  # Second positional arg is currency
