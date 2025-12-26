"""Tests for price_path_calculator_helpers.progress_emitter module."""

from unittest.mock import MagicMock

import pytest

from common.price_path_calculator_helpers.progress_emitter import emit_progress


class TestEmitProgress:
    """Tests for emit_progress function."""

    def test_calls_callback_on_interval(self) -> None:
        """Test calls callback on interval steps."""
        mock_callback = MagicMock()

        emit_progress(mock_callback, total_steps=100, current_step=10)

        mock_callback.assert_called_once_with(10, 100)

    def test_calls_callback_on_final_step(self) -> None:
        """Test calls callback on final step."""
        mock_callback = MagicMock()

        emit_progress(mock_callback, total_steps=100, current_step=100)

        mock_callback.assert_called_once_with(100, 100)

    def test_no_callback_when_none(self) -> None:
        """Test does nothing when callback is None."""
        # Should not raise
        emit_progress(None, total_steps=100, current_step=10)

    def test_no_callback_when_zero_steps(self) -> None:
        """Test does nothing when total_steps is zero."""
        mock_callback = MagicMock()

        emit_progress(mock_callback, total_steps=0, current_step=0)

        mock_callback.assert_not_called()

    def test_no_callback_when_negative_steps(self) -> None:
        """Test does nothing when total_steps is negative."""
        mock_callback = MagicMock()

        emit_progress(mock_callback, total_steps=-1, current_step=0)

        mock_callback.assert_not_called()

    def test_skips_non_interval_steps(self) -> None:
        """Test skips steps not on interval."""
        mock_callback = MagicMock()

        emit_progress(mock_callback, total_steps=100, current_step=5)

        mock_callback.assert_not_called()

    def test_handles_callback_exception(self) -> None:
        """Test handles callback exception gracefully."""
        mock_callback = MagicMock(side_effect=TypeError("Callback failed"))

        # Should not raise
        emit_progress(mock_callback, total_steps=100, current_step=10)

    def test_handles_value_error(self) -> None:
        """Test handles ValueError from callback."""
        mock_callback = MagicMock(side_effect=ValueError("Invalid value"))

        # Should not raise
        emit_progress(mock_callback, total_steps=100, current_step=10)

    def test_small_total_steps(self) -> None:
        """Test with small total steps."""
        mock_callback = MagicMock()

        emit_progress(mock_callback, total_steps=5, current_step=1)

        mock_callback.assert_called_once_with(1, 5)

    def test_interval_calculation(self) -> None:
        """Test interval is 1/10 of total."""
        mock_callback = MagicMock()

        # With 100 steps, interval is 10
        # Step 10, 20, 30, etc should trigger
        emit_progress(mock_callback, total_steps=100, current_step=20)

        mock_callback.assert_called_once_with(20, 100)
