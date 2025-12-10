"""Tests for batch validator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from common.market_data_parser_helpers.contract_validator_helpers.batch_validator import (
    BatchValidator,
)

DEFAULT_BATCH_VALID_COUNT = 2


class TestBatchValidator:
    """Tests for BatchValidator class."""

    def test_validates_all_contracts(self) -> None:
        """Validates all contracts in options data."""
        options_data = {"contract_names": ["BTC-25JAN01-100000-C", "BTC-25FEB01-95000-P"]}

        with patch(
            "common.market_data_parser_helpers.contract_validator.ContractValidator"
        ) as mock_validator:
            mock_validator.validate_contract.return_value = (True, None, {})

            valid_count, issues, stats = BatchValidator.validate_contracts(options_data, "BTC")

            assert valid_count == DEFAULT_BATCH_VALID_COUNT
            assert issues == []
            assert mock_validator.validate_contract.call_count == DEFAULT_BATCH_VALID_COUNT

    def test_counts_valid_contracts(self) -> None:
        """Counts only valid contracts."""
        options_data = {"contract_names": ["VALID-1", "INVALID-2", "VALID-3"]}

        with patch(
            "common.market_data_parser_helpers.contract_validator.ContractValidator"
        ) as mock_validator:
            mock_validator.validate_contract.side_effect = [
                (True, None, {}),
                (False, "Invalid contract", {}),
                (True, None, {}),
            ]

            valid_count, issues, stats = BatchValidator.validate_contracts(options_data, "BTC")

            assert valid_count == DEFAULT_BATCH_VALID_COUNT
            assert issues == ["Invalid contract"]

    def test_collects_error_messages(self) -> None:
        """Collects error messages from invalid contracts."""
        options_data = {"contract_names": ["INVALID-1", "INVALID-2"]}

        with patch(
            "common.market_data_parser_helpers.contract_validator.ContractValidator"
        ) as mock_validator:
            mock_validator.validate_contract.side_effect = [
                (False, "Error 1", {}),
                (False, "Error 2", {}),
            ]

            valid_count, issues, stats = BatchValidator.validate_contracts(options_data, "BTC")

            assert valid_count == 0
            assert issues == ["Error 1", "Error 2"]

    def test_aggregates_stats(self) -> None:
        """Aggregates stats from all validations."""
        options_data = {"contract_names": ["CONTRACT-1", "CONTRACT-2", "CONTRACT-3"]}

        with patch(
            "common.market_data_parser_helpers.contract_validator.ContractValidator"
        ) as mock_validator:
            mock_validator.validate_contract.side_effect = [
                (False, "Error 1", {"symbol_mismatches": 1}),
                (False, "Error 2", {"date_errors": 1}),
                (False, "Error 3", {"corrupted_years": 1, "date_errors": 1}),
            ]

            valid_count, issues, stats = BatchValidator.validate_contracts(options_data, "BTC")

            assert stats["symbol_mismatches"] == 1
            assert stats["date_errors"] == 2
            assert stats["corrupted_years"] == 1

    def test_passes_index_to_validator(self) -> None:
        """Passes correct index to validator."""
        options_data = {"contract_names": ["CONTRACT-A", "CONTRACT-B"]}

        with patch(
            "common.market_data_parser_helpers.contract_validator.ContractValidator"
        ) as mock_validator:
            mock_validator.validate_contract.return_value = (True, None, {})

            BatchValidator.validate_contracts(options_data, "ETH")

            calls = mock_validator.validate_contract.call_args_list
            assert calls[0][0][2] == 0  # First index
            assert calls[1][0][2] == 1  # Second index

    def test_handles_empty_contract_list(self) -> None:
        """Handles empty contract list."""
        options_data = {"contract_names": []}

        with patch(
            "common.market_data_parser_helpers.contract_validator.ContractValidator"
        ) as mock_validator:
            valid_count, issues, stats = BatchValidator.validate_contracts(options_data, "BTC")

            assert valid_count == 0
            assert issues == []
            assert stats == {"symbol_mismatches": 0, "date_errors": 0, "corrupted_years": 0}
            mock_validator.validate_contract.assert_not_called()

    def test_skips_none_error_messages(self) -> None:
        """Skips None error messages in issues list."""
        options_data = {"contract_names": ["CONTRACT-1"]}

        with patch(
            "common.market_data_parser_helpers.contract_validator.ContractValidator"
        ) as mock_validator:
            mock_validator.validate_contract.return_value = (False, None, {})

            valid_count, issues, stats = BatchValidator.validate_contracts(options_data, "BTC")

            assert issues == []
