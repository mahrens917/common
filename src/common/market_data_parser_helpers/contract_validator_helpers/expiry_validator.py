"""Expiry date validation utilities."""

from datetime import datetime
from typing import Any, Dict, Optional

# Constants
_CONST_3600 = 3600


class ExpiryValidator:
    """Validates expiry date consistency."""

    @staticmethod
    def validate_consistency(
        parsed_expiry: datetime,
        data_expiry: Any,
        contract_name: str,
        index: int,
        options_data: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Validate expiry consistency.

        Args:
            parsed_expiry: Expiry from parsed contract
            data_expiry: Expiry from data array
            contract_name: Contract name for error messages
            index: Index in data arrays
            options_data: Full options data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if index >= len(options_data["expiries"]):
            return True, None

        if not isinstance(data_expiry, datetime):
            return True, None

        time_diff = abs((parsed_expiry - data_expiry).total_seconds())
        if time_diff > _CONST_3600:
            error_msg = f"Expiry mismatch for {contract_name}"
            return False, error_msg

        return True, None
