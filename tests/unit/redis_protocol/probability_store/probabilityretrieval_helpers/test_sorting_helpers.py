"""Unit tests for sorting_helpers module."""

from __future__ import annotations

import pytest

from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError
from common.redis_protocol.probability_store.probabilityretrieval_helpers.sorting_helpers import (
    sort_probabilities_by_expiry_and_strike_grouped,
    split_probability_field,
)


class TestSortProbabilitiesByExpiryAndStrikeGrouped:
    """Tests for sort_probabilities_by_expiry_and_strike_grouped."""

    def test_single_entry(self) -> None:
        data = {
            "2025-01-15": {
                "call": {
                    "50000": {"probability": 0.5},
                },
            }
        }
        result = sort_probabilities_by_expiry_and_strike_grouped(data)
        assert list(result.keys()) == ["2025-01-15"]
        assert list(result["2025-01-15"].keys()) == ["call"]
        assert "50000" in result["2025-01-15"]["call"]

    def test_multiple_expiries_sorted(self) -> None:
        data = {
            "2025-03-01": {"call": {"50000": {}}},
            "2025-01-01": {"call": {"50000": {}}},
        }
        result = sort_probabilities_by_expiry_and_strike_grouped(data)
        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_multiple_strike_types_sorted(self) -> None:
        data = {
            "2025-01-01": {
                "put": {"40000": {}},
                "call": {"50000": {}},
            }
        }
        result = sort_probabilities_by_expiry_and_strike_grouped(data)
        strike_types = list(result["2025-01-01"].keys())
        assert strike_types == sorted(strike_types)

    def test_multiple_strikes_sorted(self) -> None:
        data = {
            "2025-01-01": {
                "call": {
                    "60000": {},
                    "40000": {},
                    "50000": {},
                }
            }
        }
        result = sort_probabilities_by_expiry_and_strike_grouped(data)
        strikes = list(result["2025-01-01"]["call"].keys())
        assert strikes == sorted(strikes, key=lambda x: float(x))

    def test_empty_input(self) -> None:
        result = sort_probabilities_by_expiry_and_strike_grouped({})
        assert result == {}


class TestSplitProbabilityField:
    """Tests for split_probability_field."""

    def test_iso8601_with_z(self) -> None:
        expiry, strike = split_probability_field("2025-01-01T00:00:00Z:50000")
        assert expiry == "2025-01-01T00:00:00Z"
        assert strike == "50000"

    def test_iso8601_with_offset(self) -> None:
        expiry, strike = split_probability_field("2025-01-01T00:00:00+00:00:50000")
        assert expiry == "2025-01-01T00:00:00+00:00"
        assert strike == "50000"

    def test_simple_colon_separated(self) -> None:
        expiry, strike = split_probability_field("2025-01-01:50000")
        assert expiry == "2025-01-01"
        assert strike == "50000"

    def test_raises_on_no_colon(self) -> None:
        with pytest.raises(ProbabilityStoreError, match="Invalid probability field format"):
            split_probability_field("nodivider")
