"""Structure validation helpers for market data."""

from __future__ import annotations

from typing import Any, Dict, List


class StructureValidator:
    """Validates market data structure."""

    @staticmethod
    def validate_required_keys(options_data: Dict[str, Any]) -> List[str]:
        """
        Validate that required keys exist.

        Args:
            options_data: Dictionary containing options data

        Returns:
            List of issues found
        """
        issues = []
        required_keys = ["strikes", "expiries", "implied_volatilities", "contract_names"]
        for key in required_keys:
            if key not in options_data:
                issues.append(f"Missing required key: {key}")
        return issues

    @staticmethod
    def validate_data_lengths(options_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that all data arrays have consistent lengths.

        Args:
            options_data: Dictionary containing options data

        Returns:
            (is_valid, issues)
        """
        issues = []
        required_keys = ["strikes", "expiries", "implied_volatilities", "contract_names"]

        data_lengths = [len(options_data[key]) for key in required_keys]
        if len(set(data_lengths)) > 1:
            issues.append(f"Inconsistent data lengths: {dict(zip(required_keys, data_lengths))}")
            return False, issues

        return True, issues
