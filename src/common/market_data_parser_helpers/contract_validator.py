"""Contract validation helpers for market data."""

import logging
from typing import Any, Dict, List, Optional

from ..market_data_parser import (
    DateTimeCorruptionError,
    DeribitInstrumentParser,
    ParsingError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _empty_stats() -> Dict[str, int]:
    return {
        "symbol_mismatches": 0,
        "date_errors": 0,
        "corrupted_years": 0,
    }


def _validate_contract(
    contract_name: str,
    expected_symbol: str,
    index: int,
    options_data: Dict[str, Any],
) -> tuple[bool, Optional[str], Dict[str, int]]:
    """
    Validate a single contract.

    Returns:
        (is_valid, error_message, stats_updates)
    """
    from .contract_validator_helpers import (
        CorruptionChecker,
        ExpiryValidator,
        StrikeValidator,
    )

    stats_updates = _empty_stats()

    try:
        parsed = DeribitInstrumentParser.parse_instrument(contract_name, strict_symbol=expected_symbol)

        is_corrupted, error_msg, corruption_stats = CorruptionChecker.check_year_corruption(parsed.expiry_date, contract_name)
        if is_corrupted:
            for key, value in corruption_stats.items():
                stats_updates[key] += value
            return False, error_msg, stats_updates

        data_expiry = options_data["expiries"][index] if index < len(options_data["expiries"]) else None
        is_valid, error_msg = ExpiryValidator.validate_consistency(parsed.expiry_date, data_expiry, contract_name, index, options_data)
        if not is_valid:
            stats_updates["date_errors"] = 1
            return False, error_msg, stats_updates

        data_strike = options_data["strikes"][index] if index < len(options_data["strikes"]) else None
        is_valid, error_msg = StrikeValidator.validate_consistency(parsed.strike, data_strike, contract_name, index, options_data)
        if not is_valid:
            return False, error_msg, stats_updates

        else:
            return True, None, stats_updates
    except (
        ParsingError,
        ValidationError,
        DateTimeCorruptionError,
    ) as error:
        return _handle_parsing_error(error, contract_name, stats_updates)


def _handle_parsing_error(
    error: Exception,
    contract_name: str,
    stats_updates: Dict[str, int],
) -> tuple[bool, str, Dict[str, int]]:
    error_msg = f"Invalid contract {contract_name}"
    error_str = str(error).lower()

    if "symbol mismatch" in error_str:
        stats_updates["symbol_mismatches"] = 1
    elif "date" in error_str or "corrupted" in error_str:
        stats_updates["date_errors"] = 1
        if "corrupted" in error_str:
            stats_updates["corrupted_years"] = 1

    return False, error_msg, stats_updates


def _validate_all_contracts(options_data: Dict[str, Any], expected_symbol: str) -> tuple[int, List[str], Dict[str, int]]:
    """
    Validate all contracts in the data.

    Returns:
        (valid_count, issues, stats)
    """
    issues: List[str] = []
    stats = _empty_stats()
    valid_count = 0

    for i, contract_name in enumerate(options_data["contract_names"]):
        is_valid, error_msg, updates = _validate_contract(contract_name, expected_symbol, i, options_data)

        if is_valid:
            valid_count += 1
        elif error_msg:
            issues.append(error_msg)

        for key, value in updates.items():
            stats[key] += value

    return valid_count, issues, stats


class ContractValidator:
    """Validates individual contracts."""

    @staticmethod
    def validate_contract(
        contract_name: str,
        expected_symbol: str,
        index: int,
        options_data: Dict[str, Any],
    ) -> tuple[bool, Optional[str], Dict[str, int]]:
        return _validate_contract(contract_name, expected_symbol, index, options_data)

    @staticmethod
    def validate_all_contracts(options_data: Dict[str, Any], expected_symbol: str) -> tuple[int, List[str], Dict[str, int]]:
        return _validate_all_contracts(options_data, expected_symbol)
