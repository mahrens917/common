"""Tests for validation workflow module."""

from unittest.mock import MagicMock, patch

from common.market_data_parser_helpers.contract_validator_helpers.validation_workflow import (
    ValidationWorkflow,
)


class TestValidationWorkflowExecute:
    """Tests for ValidationWorkflow.execute."""

    def test_returns_valid_when_all_checks_pass(self) -> None:
        """Returns (True, None, stats) when all validations pass."""
        mock_parsed = MagicMock()
        mock_parsed.expiry_date = "2024-12-01"
        mock_parsed.strike = 50000.0

        with patch(
            "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ContractParser"
        ) as mock_parser:
            with patch(
                "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.CorruptionChecker"
            ) as mock_corruption:
                with patch(
                    "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ExpiryValidator"
                ) as mock_expiry:
                    with patch(
                        "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.StrikeValidator"
                    ) as mock_strike:
                        mock_parser.parse_instrument.return_value = mock_parsed
                        mock_corruption.check_year_corruption.return_value = (
                            False,
                            None,
                            {},
                        )
                        mock_expiry.validate_consistency.return_value = (True, None)
                        mock_strike.validate_consistency.return_value = (True, None)

                        options_data = {
                            "expiries": ["2024-12-01"],
                            "strikes": [50000.0],
                        }

                        is_valid, error, stats = ValidationWorkflow.execute(
                            "BTC-25DEC01-50000-C",
                            "BTC",
                            0,
                            options_data,
                        )

                        assert is_valid is True
                        assert error is None

    def test_returns_invalid_when_year_corrupted(self) -> None:
        """Returns (False, error, stats) when year is corrupted."""
        mock_parsed = MagicMock()
        mock_parsed.expiry_date = "2099-12-01"

        with patch(
            "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ContractParser"
        ) as mock_parser:
            with patch(
                "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.CorruptionChecker"
            ) as mock_corruption:
                with patch(
                    "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ErrorHandler"
                ) as mock_error:
                    mock_parser.parse_instrument.return_value = mock_parsed
                    mock_corruption.check_year_corruption.return_value = (
                        True,
                        "Corrupted year",
                        {"corrupted_years": 1},
                    )
                    mock_error.merge_stats.return_value = (
                        False,
                        "Corrupted year",
                        {"corrupted_years": 1},
                    )

                    options_data = {"expiries": [], "strikes": []}

                    is_valid, error, stats = ValidationWorkflow.execute(
                        "BTC-99DEC01-50000-C",
                        "BTC",
                        0,
                        options_data,
                    )

                    assert is_valid is False
                    assert error is not None

    def test_returns_invalid_when_expiry_mismatch(self) -> None:
        """Returns (False, error, stats) when expiry doesn't match."""
        mock_parsed = MagicMock()
        mock_parsed.expiry_date = "2024-12-01"
        mock_parsed.strike = 50000.0

        with patch(
            "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ContractParser"
        ) as mock_parser:
            with patch(
                "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.CorruptionChecker"
            ) as mock_corruption:
                with patch(
                    "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ExpiryValidator"
                ) as mock_expiry:
                    mock_parser.parse_instrument.return_value = mock_parsed
                    mock_corruption.check_year_corruption.return_value = (False, None, {})
                    mock_expiry.validate_consistency.return_value = (
                        False,
                        "Expiry mismatch",
                    )

                    options_data = {
                        "expiries": ["2024-12-15"],
                        "strikes": [50000.0],
                    }

                    is_valid, error, stats = ValidationWorkflow.execute(
                        "BTC-25DEC01-50000-C",
                        "BTC",
                        0,
                        options_data,
                    )

                    assert is_valid is False
                    assert stats["date_errors"] == 1

    def test_returns_invalid_when_strike_mismatch(self) -> None:
        """Returns (False, error, stats) when strike doesn't match."""
        mock_parsed = MagicMock()
        mock_parsed.expiry_date = "2024-12-01"
        mock_parsed.strike = 50000.0

        with patch(
            "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ContractParser"
        ) as mock_parser:
            with patch(
                "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.CorruptionChecker"
            ) as mock_corruption:
                with patch(
                    "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.ExpiryValidator"
                ) as mock_expiry:
                    with patch(
                        "common.market_data_parser_helpers.contract_validator_helpers.validation_workflow.StrikeValidator"
                    ) as mock_strike:
                        mock_parser.parse_instrument.return_value = mock_parsed
                        mock_corruption.check_year_corruption.return_value = (
                            False,
                            None,
                            {},
                        )
                        mock_expiry.validate_consistency.return_value = (True, None)
                        mock_strike.validate_consistency.return_value = (
                            False,
                            "Strike mismatch",
                        )

                        options_data = {
                            "expiries": ["2024-12-01"],
                            "strikes": [60000.0],
                        }

                        is_valid, error, stats = ValidationWorkflow.execute(
                            "BTC-25DEC01-50000-C",
                            "BTC",
                            0,
                            options_data,
                        )

                        assert is_valid is False
                        assert error is not None
