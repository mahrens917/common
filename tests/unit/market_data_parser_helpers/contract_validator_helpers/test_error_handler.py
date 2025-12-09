"""Tests for error handler."""

from __future__ import annotations

from src.common.market_data_parser_helpers.contract_validator_helpers.error_handler import (
    ErrorHandler,
)


class TestHandleParsingError:
    """Tests for handle_parsing_error method."""

    def test_handles_symbol_mismatch_error(self) -> None:
        """Updates stats for symbol mismatch error."""
        error = ValueError("Symbol mismatch: expected BTC, got ETH")
        stats = {}

        is_valid, error_msg, updated_stats = ErrorHandler.handle_parsing_error(
            error, "BTC-25JAN01-100000-C", stats
        )

        assert is_valid is False
        assert error_msg == "Invalid contract BTC-25JAN01-100000-C"
        assert updated_stats["symbol_mismatches"] == 1

    def test_handles_date_error(self) -> None:
        """Updates stats for date error."""
        error = ValueError("Invalid date format")
        stats = {}

        is_valid, error_msg, updated_stats = ErrorHandler.handle_parsing_error(
            error, "BTC-INVALID-100000-C", stats
        )

        assert is_valid is False
        assert updated_stats["date_errors"] == 1

    def test_handles_corrupted_date_error(self) -> None:
        """Updates stats for corrupted date error."""
        error = ValueError("Corrupted year: 2099")
        stats = {}

        is_valid, error_msg, updated_stats = ErrorHandler.handle_parsing_error(
            error, "BTC-25JAN99-100000-C", stats
        )

        assert is_valid is False
        assert updated_stats["date_errors"] == 1
        assert updated_stats["corrupted_years"] == 1

    def test_handles_generic_error(self) -> None:
        """Handles generic error without specific stats update."""
        error = RuntimeError("Unknown error")
        stats = {}

        is_valid, error_msg, updated_stats = ErrorHandler.handle_parsing_error(
            error, "INVALID", stats
        )

        assert is_valid is False
        assert error_msg == "Invalid contract INVALID"
        assert "symbol_mismatches" not in updated_stats
        assert "date_errors" not in updated_stats

    def test_error_message_contains_contract_name(self) -> None:
        """Error message contains contract name."""
        error = ValueError("test")

        _, error_msg, _ = ErrorHandler.handle_parsing_error(error, "TEST-CONTRACT-NAME", {})

        assert "TEST-CONTRACT-NAME" in error_msg


class TestMergeStats:
    """Tests for merge_stats method."""

    def test_merges_stats_into_base(self) -> None:
        """Merges new stats into base stats."""
        base_stats = {"errors": 5, "symbol_mismatches": 2, "date_errors": 0}
        new_stats = {"errors": 3, "date_errors": 1}

        is_valid, error_msg, merged = ErrorHandler.merge_stats(
            False, "test error", base_stats, new_stats
        )

        assert is_valid is False
        assert error_msg == "test error"
        assert merged["errors"] == 8
        assert merged["symbol_mismatches"] == 2
        assert merged["date_errors"] == 1

    def test_passes_through_validity_and_message(self) -> None:
        """Passes through is_valid and error_msg unchanged."""
        is_valid, error_msg, _ = ErrorHandler.merge_stats(True, "success", {}, {})

        assert is_valid is True
        assert error_msg == "success"

    def test_handles_empty_new_stats(self) -> None:
        """Handles empty new_stats dict."""
        base_stats = {"errors": 5}

        _, _, merged = ErrorHandler.merge_stats(False, "error", base_stats, {})

        assert merged["errors"] == 5

    def test_handles_matching_keys(self) -> None:
        """Handles new stats with keys already in base."""
        base_stats = {"errors": 3}
        new_stats = {"errors": 2}

        _, _, merged = ErrorHandler.merge_stats(False, "error", base_stats, new_stats)

        assert merged["errors"] == 5
