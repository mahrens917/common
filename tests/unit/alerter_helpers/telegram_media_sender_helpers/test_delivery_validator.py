"""Tests for alerter_helpers.telegram_media_sender_helpers.delivery_validator module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from common.alerter_helpers.telegram_media_sender_helpers.delivery_validator import (
    DeliveryValidator,
)


class TestDeliveryValidatorValidateRequest:
    """Tests for validate_request static method."""

    def test_raises_on_empty_recipients(self) -> None:
        """Test raises ValueError on empty recipients."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            mock_backoff = MagicMock()
            mock_backoff.should_skip_operation.return_value = False

            with pytest.raises(ValueError) as exc_info:
                DeliveryValidator.validate_request([], path, None, mock_backoff, "sendPhoto")

            assert "recipient" in str(exc_info.value).lower()
        finally:
            path.unlink()

    def test_raises_on_missing_source_file(self) -> None:
        """Test raises FileNotFoundError when source file missing."""
        mock_backoff = MagicMock()
        mock_backoff.should_skip_operation.return_value = False

        with pytest.raises(FileNotFoundError) as exc_info:
            DeliveryValidator.validate_request(["user1"], Path("/nonexistent/file.png"), None, mock_backoff, "sendPhoto")

        assert "missing" in str(exc_info.value).lower()

    def test_raises_on_missing_spooled_file(self) -> None:
        """Test raises FileNotFoundError when spooled file missing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            source_path = Path(f.name)

        try:
            mock_backoff = MagicMock()
            mock_backoff.should_skip_operation.return_value = False

            with pytest.raises(FileNotFoundError):
                DeliveryValidator.validate_request(["user1"], source_path, Path("/nonexistent/spooled.png"), mock_backoff, "sendPhoto")
        finally:
            source_path.unlink()

    def test_raises_on_backoff_active(self) -> None:
        """Test raises RuntimeError when backoff is active."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            mock_backoff = MagicMock()
            mock_backoff.should_skip_operation.return_value = True

            with pytest.raises(RuntimeError) as exc_info:
                DeliveryValidator.validate_request(["user1"], path, None, mock_backoff, "sendPhoto")

            assert "backoff" in str(exc_info.value).lower()
        finally:
            path.unlink()

    def test_returns_source_path_when_no_spooled(self) -> None:
        """Test returns source path when no spooled path provided."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            source_path = Path(f.name)

        try:
            mock_backoff = MagicMock()
            mock_backoff.should_skip_operation.return_value = False

            result = DeliveryValidator.validate_request(["user1"], source_path, None, mock_backoff, "sendPhoto")

            assert result == source_path
        finally:
            source_path.unlink()

    def test_returns_spooled_path_when_provided(self) -> None:
        """Test returns spooled path when provided."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"source")
            source_path = Path(f.name)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"spooled")
            spooled_path = Path(f.name)

        try:
            mock_backoff = MagicMock()
            mock_backoff.should_skip_operation.return_value = False

            result = DeliveryValidator.validate_request(["user1"], source_path, spooled_path, mock_backoff, "sendPhoto")

            assert result == spooled_path
        finally:
            source_path.unlink()
            spooled_path.unlink()

    def test_checks_backoff_for_correct_method(self) -> None:
        """Test checks backoff with correct method name."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            path = Path(f.name)

        try:
            mock_backoff = MagicMock()
            mock_backoff.should_skip_operation.return_value = False

            DeliveryValidator.validate_request(["user1"], path, None, mock_backoff, "sendDocument")

            mock_backoff.should_skip_operation.assert_called_once_with("sendDocument")
        finally:
            path.unlink()


class TestDeliveryValidatorVerifySuccess:
    """Tests for verify_success static method."""

    def test_raises_on_zero_successes(self) -> None:
        """Test raises RuntimeError on zero successes."""
        with pytest.raises(RuntimeError) as exc_info:
            DeliveryValidator.verify_success(0)

        assert "zero successes" in str(exc_info.value).lower()

    def test_passes_on_positive_successes(self) -> None:
        """Test passes when success count is positive."""
        # Should not raise
        DeliveryValidator.verify_success(1)
        DeliveryValidator.verify_success(5)
        DeliveryValidator.verify_success(100)
