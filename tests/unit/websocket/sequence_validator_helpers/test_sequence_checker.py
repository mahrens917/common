"""Tests for sequence checker module."""

from unittest.mock import MagicMock, patch

import pytest

from src.common.websocket.sequence_validator_helpers.sequence_checker import (
    SequenceChecker,
    SequenceGapError,
)

DEFAULT_SEQUENCE_MAX_GAP_SIZE = 10
EXPECTED_GAP_SIZE = 5


class TestSequenceGapError:
    """Tests for SequenceGapError exception."""

    def test_is_exception(self) -> None:
        """Is a subclass of Exception."""
        error = SequenceGapError("test message")

        assert isinstance(error, Exception)

    def test_has_message(self) -> None:
        """Has the provided message."""
        error = SequenceGapError("gap detected")

        assert str(error) == "gap detected"


class TestSequenceChecker:
    """Tests for SequenceChecker class."""

    def test_init_stores_parameters(self) -> None:
        """Stores initialization parameters."""
        mock_state = MagicMock()
        checker = SequenceChecker("deribit", DEFAULT_SEQUENCE_MAX_GAP_SIZE, mock_state)

        assert checker.service_name == "deribit"
        assert checker.max_gap_tolerance == 10
        assert checker.tracking_state is mock_state

    def test_validate_sequence_initializes_new_sid(self) -> None:
        """Initializes tracking for new SID."""
        mock_state = MagicMock()
        mock_state.has_sid.return_value = False
        checker = SequenceChecker("deribit", DEFAULT_SEQUENCE_MAX_GAP_SIZE, mock_state)

        is_valid, gap_size = checker.validate_sequence(123, 100)

        mock_state.initialize_sid.assert_called_once_with(123, 100)
        assert is_valid is True
        assert gap_size is None

    def test_validate_sequence_accepts_expected_sequence(self) -> None:
        """Accepts expected sequence number."""
        mock_state = MagicMock()
        mock_state.has_sid.return_value = True
        mock_state.get_last_seq.return_value = 99
        checker = SequenceChecker("deribit", DEFAULT_SEQUENCE_MAX_GAP_SIZE, mock_state)

        is_valid, gap_size = checker.validate_sequence(123, 100)

        mock_state.update_sequence.assert_called_once_with(123, 100)
        mock_state.reset_gap_count.assert_called_once_with(123)
        assert is_valid is True
        assert gap_size is None

    def test_validate_sequence_detects_gap(self) -> None:
        """Detects gap when sequence skips."""
        mock_state = MagicMock()
        mock_state.has_sid.return_value = True
        mock_state.get_last_seq.return_value = 99
        mock_state.get_gap_count.return_value = EXPECTED_GAP_SIZE
        checker = SequenceChecker("deribit", DEFAULT_SEQUENCE_MAX_GAP_SIZE, mock_state)

        with patch("src.common.websocket.sequence_validator_helpers.sequence_checker.logger"):
            is_valid, gap_size = checker.validate_sequence(123, 105)

        mock_state.increment_gap_count.assert_called_once_with(123, EXPECTED_GAP_SIZE)
        mock_state.update_sequence.assert_called_once_with(123, 105)
        assert is_valid is False
        assert gap_size == EXPECTED_GAP_SIZE

    def test_validate_sequence_raises_on_tolerance_exceeded(self) -> None:
        """Raises SequenceGapError when tolerance exceeded."""
        mock_state = MagicMock()
        mock_state.has_sid.return_value = True
        mock_state.get_last_seq.return_value = 99
        mock_state.get_gap_count.return_value = 15
        checker = SequenceChecker("deribit", DEFAULT_SEQUENCE_MAX_GAP_SIZE, mock_state)

        with patch("src.common.websocket.sequence_validator_helpers.sequence_checker.logger"):
            with pytest.raises(SequenceGapError) as exc_info:
                checker.validate_sequence(123, 105)

        assert "tolerance exceeded" in str(exc_info.value)

    def test_validate_sequence_detects_out_of_order(self) -> None:
        """Detects out-of-order messages."""
        mock_state = MagicMock()
        mock_state.has_sid.return_value = True
        mock_state.get_last_seq.return_value = 100
        checker = SequenceChecker("deribit", 10, mock_state)

        with patch("src.common.websocket.sequence_validator_helpers.sequence_checker.logger"):
            is_valid, gap_size = checker.validate_sequence(123, 95)

        mock_state.update_sequence.assert_not_called()
        assert is_valid is False
        assert gap_size is None
