"""Validation workflow orchestration."""

from typing import Any, Dict, Optional

from .contract_parser import ContractParser
from .corruption_checker import CorruptionChecker
from .error_handler import ErrorHandler
from .expiry_validator import ExpiryValidator
from .strike_validator import StrikeValidator


class ValidationWorkflow:
    """Orchestrates the contract validation workflow."""

    @staticmethod
    def execute(
        contract_name: str,
        expected_symbol: str,
        index: int,
        options_data: Dict[str, Any],
    ) -> tuple[bool, Optional[str], Dict[str, int]]:
        """
        Execute validation workflow for a single contract.

        Args:
            contract_name: Contract name to validate
            expected_symbol: Expected symbol
            index: Index in data arrays
            options_data: Full options data dict

        Returns:
            (is_valid, error_message, stats_updates)
        """
        stats_updates = {
            "symbol_mismatches": 0,
            "date_errors": 0,
            "corrupted_years": 0,
        }

        parsed = ContractParser.parse_instrument(contract_name, expected_symbol)

        is_corrupted, error_msg, corruption_stats = CorruptionChecker.check_year_corruption(
            parsed.expiry_date, contract_name
        )
        if is_corrupted:
            return ErrorHandler.merge_stats(False, error_msg, stats_updates, corruption_stats)

        data_expiry = (
            options_data["expiries"][index] if index < len(options_data["expiries"]) else None
        )
        is_valid, error_msg = ExpiryValidator.validate_consistency(
            parsed.expiry_date, data_expiry, contract_name, index, options_data
        )
        if not is_valid:
            stats_updates["date_errors"] = 1
            return False, error_msg, stats_updates

        data_strike = (
            options_data["strikes"][index] if index < len(options_data["strikes"]) else None
        )
        is_valid, error_msg = StrikeValidator.validate_consistency(
            parsed.strike, data_strike, contract_name, index, options_data
        )
        if not is_valid:
            return False, error_msg, stats_updates

        return True, None, stats_updates
