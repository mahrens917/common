"""Error handling for contract validation."""

from typing import Dict


class ErrorHandler:
    """Handles parsing errors and stats updates."""

    @staticmethod
    def handle_parsing_error(
        error: Exception, contract_name: str, stats_updates: Dict[str, int]
    ) -> tuple[bool, str, Dict[str, int]]:
        """Handle parsing errors and update stats."""
        error_msg = f"Invalid contract {contract_name}"
        error_str = str(error).lower()

        if "symbol mismatch" in error_str:
            stats_updates["symbol_mismatches"] = 1
        elif "date" in error_str or "corrupted" in error_str:
            stats_updates["date_errors"] = 1
            if "corrupted" in error_str:
                stats_updates["corrupted_years"] = 1

        return False, error_msg, stats_updates

    @staticmethod
    def merge_stats(
        is_valid: bool, error_msg: str, base_stats: Dict[str, int], new_stats: Dict[str, int]
    ) -> tuple[bool, str, Dict[str, int]]:
        """Merge stats dictionaries."""
        for key, value in new_stats.items():
            base_stats[key] += value
        return is_valid, error_msg, base_stats
