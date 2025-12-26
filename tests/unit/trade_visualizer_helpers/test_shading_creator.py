"""Tests for trade_visualizer_helpers.shading_creator module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from common.trade_visualizer_helpers.shading_creator import (
    create_executed_trade_shading,
    create_no_liquidity_shading,
    is_no_liquidity_state,
    safe_float,
)


class TestCreateExecutedTradeShading:
    """Tests for create_executed_trade_shading function."""

    def test_delegates_to_builder(self) -> None:
        """Test delegates to shading builder."""
        mock_builder = MagicMock()
        mock_trade = MagicMock()
        strikes = [70.0, 75.0]
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]
        expected_result = MagicMock()
        mock_builder.create_executed_trade_shading.return_value = expected_result

        result = create_executed_trade_shading(mock_builder, mock_trade, strikes, timestamps)

        assert result == expected_result
        mock_builder.create_executed_trade_shading.assert_called_once_with(mock_trade, strikes, timestamps)


class TestCreateNoLiquidityShading:
    """Tests for create_no_liquidity_shading function."""

    def test_delegates_to_builder(self) -> None:
        """Test delegates to shading builder."""
        mock_builder = MagicMock()
        mock_state = MagicMock()
        strikes = [70.0, 75.0]
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]
        expected_result = MagicMock()
        mock_builder.create_no_liquidity_shading.return_value = expected_result

        result = create_no_liquidity_shading(mock_builder, mock_state, strikes, timestamps)

        assert result == expected_result
        mock_builder.create_no_liquidity_shading.assert_called_once_with(mock_state, strikes, timestamps)


class TestIsNoLiquidityState:
    """Tests for is_no_liquidity_state function."""

    def test_delegates_to_builder(self) -> None:
        """Test delegates to shading builder."""
        mock_builder = MagicMock()
        mock_state = MagicMock()
        mock_builder.is_no_liquidity_state.return_value = True

        result = is_no_liquidity_state(mock_builder, mock_state)

        assert result is True
        mock_builder.is_no_liquidity_state.assert_called_once_with(mock_state)


class TestSafeFloat:
    """Tests for safe_float function."""

    def test_delegates_to_fetcher(self) -> None:
        """Test delegates to liquidity fetcher."""
        mock_fetcher = MagicMock()
        mock_fetcher.safe_float.return_value = 42.5

        result = safe_float(mock_fetcher, "42.5")

        assert result == 42.5
        mock_fetcher.safe_float.assert_called_once_with("42.5")
