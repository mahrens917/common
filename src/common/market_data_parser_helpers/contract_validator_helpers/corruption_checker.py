"""Datetime corruption detection utilities."""

from datetime import datetime
from typing import Dict

# Constants
_CONST_2050 = 2050


class CorruptionChecker:
    """Checks for datetime corruption issues."""

    @staticmethod
    def check_year_corruption(expiry_date: datetime, contract_name: str) -> tuple[bool, str, Dict[str, int]]:
        """
        Check for corrupted year values.

        Args:
            expiry_date: Expiry date to check
            contract_name: Contract name for error messages

        Returns:
            Tuple of (is_corrupted, error_message, stats_updates)
        """
        stats_updates = {
            "corrupted_years": 0,
            "date_errors": 0,
        }

        if expiry_date.year in [2520, 2620] or expiry_date.year > _CONST_2050:
            error_msg = f"DATETIME CORRUPTION: {contract_name} has year {expiry_date.year}"
            stats_updates["corrupted_years"] = 1
            stats_updates["date_errors"] = 1
            return True, error_msg, stats_updates

        return False, "", stats_updates
