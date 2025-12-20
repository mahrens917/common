"""Strike price validation utilities."""

from __future__ import annotations

from typing import Any, Dict, Optional

# Constants
_CONST_0_01 = 0.01


class StrikeValidator:
    """Validates strike price consistency."""

    @staticmethod
    def validate_consistency(
        parsed_strike: Optional[float],
        data_strike: Any,
        contract_name: str,
        index: int,
        options_data: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Validate strike consistency.

        Args:
            parsed_strike: Strike from parsed contract
            data_strike: Strike from data array
            contract_name: Contract name for error messages
            index: Index in data arrays
            options_data: Full options data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if index >= len(options_data["strikes"]):
            return True, None

        if parsed_strike is None:
            _none_guard_value = True, None
            return _none_guard_value

        if abs(parsed_strike - data_strike) > _CONST_0_01:
            error_msg = f"Strike mismatch for {contract_name}"
            return False, error_msg

        return True, None
