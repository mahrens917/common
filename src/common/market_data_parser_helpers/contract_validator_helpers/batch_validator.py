"""Batch validation of contracts."""

from typing import Any, Dict, List


class BatchValidator:
    """Validates multiple contracts at once."""

    @staticmethod
    def validate_contracts(options_data: Dict[str, Any], expected_symbol: str) -> tuple[int, List[str], Dict[str, int]]:
        """Validate all contracts in options data."""
        from ..contract_validator import ContractValidator

        issues = []
        stats = {"symbol_mismatches": 0, "date_errors": 0, "corrupted_years": 0}
        valid_count = 0

        for i, contract_name in enumerate(options_data["contract_names"]):
            is_valid, error_msg, updates = ContractValidator.validate_contract(contract_name, expected_symbol, i, options_data)

            if is_valid:
                valid_count += 1
            elif error_msg:
                issues.append(error_msg)

            for key, value in updates.items():
                stats[key] += value

        return valid_count, issues, stats
