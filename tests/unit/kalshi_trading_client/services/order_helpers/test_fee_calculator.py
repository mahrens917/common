"""Tests for fee_calculator module."""

from unittest.mock import MagicMock, patch

import pytest

from common.kalshi_trading_client.services.order_helpers.fee_calculator import (
    FeeCalculator,
    calculate_order_fees,
)


class TestFeeCalculator:
    """Tests for FeeCalculator class."""

    @pytest.mark.asyncio
    async def test_calculate_order_fees_success(self):
        with patch("common.kalshi_trading_client.services.order_helpers.fee_calculator.importlib") as mock_importlib:
            mock_module = MagicMock()
            mock_module.calculate_fees = MagicMock(return_value=50)
            mock_importlib.import_module.return_value = mock_module

            result = await FeeCalculator.calculate_order_fees("TICKER-ABC", 10, 5000)

            assert result == 50

    @pytest.mark.asyncio
    async def test_calculate_order_fees_passes_is_maker(self):
        with patch("common.kalshi_trading_client.services.order_helpers.fee_calculator.importlib") as mock_importlib:
            mock_module = MagicMock()
            mock_module.calculate_fees = MagicMock(return_value=12)
            mock_importlib.import_module.return_value = mock_module

            result = await FeeCalculator.calculate_order_fees("TICKER-ABC", 10, 5000, is_maker=True)

            assert result == 12
            mock_module.calculate_fees.assert_called_once_with(10, 5000, "TICKER-ABC", is_maker=True)

    @pytest.mark.asyncio
    async def test_calculate_order_fees_uses_fallback_on_attribute_error(self):
        with patch("common.kalshi_trading_client.services.order_helpers.fee_calculator.importlib") as mock_importlib:
            mock_module = MagicMock(spec=[])
            mock_importlib.import_module.return_value = mock_module

            with patch("common.kalshi_fees.calculate_fees", return_value=75) as mock_fee_func:
                result = await FeeCalculator.calculate_order_fees("TICKER-XYZ", 5, 3000)

                assert result == 75
                mock_fee_func.assert_called_once_with(5, 3000, "TICKER-XYZ", is_maker=False)

    @pytest.mark.asyncio
    async def test_calculate_order_fees_raises_on_calculation_error(self):
        with patch("common.kalshi_trading_client.services.order_helpers.fee_calculator.importlib") as mock_importlib:
            mock_module = MagicMock()
            mock_module.calculate_fees = MagicMock(side_effect=ValueError("Invalid input"))
            mock_importlib.import_module.return_value = mock_module

            with pytest.raises(ValueError, match="Cannot calculate fees"):
                await FeeCalculator.calculate_order_fees("TICKER-ERR", 10, 5000)

    @pytest.mark.asyncio
    async def test_calculate_order_fees_raises_on_type_error(self):
        with patch("common.kalshi_trading_client.services.order_helpers.fee_calculator.importlib") as mock_importlib:
            mock_module = MagicMock()
            mock_module.calculate_fees = MagicMock(side_effect=TypeError("Type mismatch"))
            mock_importlib.import_module.return_value = mock_module

            with pytest.raises(ValueError, match="Cannot calculate fees"):
                await FeeCalculator.calculate_order_fees("TICKER-ERR", 10, 5000)


class TestModuleLevelFunction:
    """Tests for module-level calculate_order_fees function."""

    @pytest.mark.asyncio
    async def test_module_function_is_class_method(self):
        assert calculate_order_fees is FeeCalculator.calculate_order_fees
