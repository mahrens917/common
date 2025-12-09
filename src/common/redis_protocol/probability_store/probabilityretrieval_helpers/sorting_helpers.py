from __future__ import annotations

"""Sorting and field parsing utilities for probability retrieval."""


from typing import Dict, Mapping, Tuple, Union

from ..exceptions import ProbabilityStoreError
from ..keys import expiry_sort_key, strike_sort_key

ProbabilityFields = Dict[str, Union[str, float]]
ProbabilityByStrike = Dict[str, ProbabilityFields]
ProbabilityByStrikeType = Dict[str, ProbabilityByStrike]
ProbabilityByExpiryGrouped = Dict[str, ProbabilityByStrikeType]


def sort_probabilities_by_expiry_and_strike(
    result: Mapping[str, Mapping[str, ProbabilityFields]],
) -> Dict[str, Dict[str, ProbabilityFields]]:
    """Sort probability result by expiry (chronological) and strike (numeric).

    Args:
        result: Nested dict of {expiry: {strike: {field: value}}}

    Returns:
        Same structure, sorted by expiry then strike
    """
    sorted_result: Dict[str, Dict[str, ProbabilityFields]] = {}

    for expiry in sorted(result.keys(), key=lambda x: expiry_sort_key(x)):
        strikes_for_expiry = result[expiry]
        sorted_strikes = sorted(strikes_for_expiry.keys(), key=strike_sort_key)
        sorted_result[expiry] = {strike: strikes_for_expiry[strike] for strike in sorted_strikes}

    return sorted_result


def sort_probabilities_by_expiry_and_strike_grouped(
    result: Mapping[str, Mapping[str, Mapping[str, ProbabilityFields]]],
) -> ProbabilityByExpiryGrouped:
    """Sort grouped probability result (with strike_type layer).

    Args:
        result: Nested dict of {expiry: {strike_type: {strike: {field: value}}}}

    Returns:
        Same structure, sorted by expiry, strike_type, then strike
    """
    sorted_result: ProbabilityByExpiryGrouped = {}

    for expiry in sorted(result.keys(), key=lambda x: expiry_sort_key(x)):
        strike_type_map = result[expiry]
        sorted_strike_types = sorted(strike_type_map.keys())

        strike_type_bucket: ProbabilityByStrikeType = {}
        for strike_type in sorted_strike_types:
            strikes = strike_type_map[strike_type]
            sorted_strikes = sorted(strikes.items(), key=lambda item: strike_sort_key(item[0]))
            strike_type_bucket[strike_type] = {key: value for key, value in sorted_strikes}

        sorted_result[expiry] = strike_type_bucket

    return sorted_result


def split_probability_field(field: str) -> Tuple[str, str]:
    """Split probability field into expiry and strike components.

    Handles three formats:
    - ISO8601 with Z: "2025-01-01T00:00:00Z:50000"
    - ISO8601 with offset: "2025-01-01T00:00:00+00:00:50000"
    - Simple colon-separated: "2025-01-01:50000"

    Args:
        field: Field string to split

    Returns:
        Tuple of (expiry, strike)

    Raises:
        ProbabilityStoreError: If field format is invalid
    """
    z_colon_index = field.find("Z:")
    if z_colon_index != -1:
        expiry = field[: z_colon_index + 1]
        strike = field[z_colon_index + 2 :]
        return expiry, strike

    plus_index = field.find("+00:00:")
    if plus_index != -1:
        expiry = field[: plus_index + 6]
        strike = field[plus_index + 7 :]
        return expiry, strike

    last_colon_index = field.rfind(":")
    if last_colon_index == -1:
        raise ProbabilityStoreError(f"Invalid probability field format: {field}")

    expiry = field[:last_colon_index]
    strike = field[last_colon_index + 1 :]
    return expiry, strike


__all__ = [
    "sort_probabilities_by_expiry_and_strike",
    "sort_probabilities_by_expiry_and_strike_grouped",
    "split_probability_field",
]
