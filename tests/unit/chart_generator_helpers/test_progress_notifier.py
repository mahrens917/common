"""Tests for chart_generator_helpers.progress_notifier module."""

from unittest.mock import MagicMock

import pytest

from common.chart_generator.exceptions import ProgressNotificationError
from common.chart_generator_helpers.progress_notifier import ProgressNotifier


class TestProgressNotifierInit:
    """Tests for ProgressNotifier initialization."""

    def test_stores_callback(self) -> None:
        """Test stores callback."""
        callback = MagicMock()
        notifier = ProgressNotifier(progress_callback=callback)

        assert notifier._progress_callback is callback

    def test_accepts_none_callback(self) -> None:
        """Test accepts None callback."""
        notifier = ProgressNotifier(progress_callback=None)

        assert notifier._progress_callback is None

    def test_defaults_to_none(self) -> None:
        """Test defaults to None when no callback provided."""
        notifier = ProgressNotifier()

        assert notifier._progress_callback is None


class TestProgressNotifierNotifyProgress:
    """Tests for notify_progress method."""

    def test_calls_callback_with_message(self) -> None:
        """Test calls callback with message."""
        callback = MagicMock()
        notifier = ProgressNotifier(progress_callback=callback)

        notifier.notify_progress("Processing chart...")

        callback.assert_called_once_with("Processing chart...")

    def test_does_nothing_when_no_callback(self) -> None:
        """Test does nothing when callback is None."""
        notifier = ProgressNotifier(progress_callback=None)

        # Should not raise
        notifier.notify_progress("Test message")

    def test_raises_on_runtime_error(self) -> None:
        """Test raises ProgressNotificationError on RuntimeError."""
        callback = MagicMock(side_effect=RuntimeError("Callback failed"))
        notifier = ProgressNotifier(progress_callback=callback)

        with pytest.raises(ProgressNotificationError) as exc_info:
            notifier.notify_progress("Message")

        assert "Progress callback failed" in str(exc_info.value)

    def test_raises_on_value_error(self) -> None:
        """Test raises ProgressNotificationError on ValueError."""
        callback = MagicMock(side_effect=ValueError("Invalid value"))
        notifier = ProgressNotifier(progress_callback=callback)

        with pytest.raises(ProgressNotificationError):
            notifier.notify_progress("Message")

    def test_raises_on_type_error(self) -> None:
        """Test raises ProgressNotificationError on TypeError."""
        callback = MagicMock(side_effect=TypeError("Type error"))
        notifier = ProgressNotifier(progress_callback=callback)

        with pytest.raises(ProgressNotificationError):
            notifier.notify_progress("Message")

    def test_passes_through_on_success(self) -> None:
        """Test passes through when callback succeeds."""
        callback = MagicMock(return_value=None)
        notifier = ProgressNotifier(progress_callback=callback)

        # Should not raise
        notifier.notify_progress("Success")

        callback.assert_called_once()

    def test_preserves_original_exception_chain(self) -> None:
        """Test preserves original exception in chain."""
        original_error = RuntimeError("Original error")
        callback = MagicMock(side_effect=original_error)
        notifier = ProgressNotifier(progress_callback=callback)

        with pytest.raises(ProgressNotificationError) as exc_info:
            notifier.notify_progress("Message")

        assert exc_info.value.__cause__ is original_error
