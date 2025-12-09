"""Tests for strike price validation utilities."""

from types import SimpleNamespace

import pytest

from src.common.market_data_parser_helpers.contract_validator_helpers.strike_validator import (
    StrikeValidator,
)


def test_validate_consistency_accepts_matching_strike():
    options_data = {"strikes": [100]}
    is_valid, error = StrikeValidator.validate_consistency(
        parsed_strike=100.0,
        data_strike=99.995,
        contract_name="test",
        index=0,
        options_data=options_data,
    )
    assert is_valid
    assert error is None


def test_validate_consistency_skips_out_of_range_index():
    options_data = {"strikes": [100]}
    is_valid, error = StrikeValidator.validate_consistency(
        parsed_strike=110.0,
        data_strike=100.0,
        contract_name="test",
        index=2,
        options_data=options_data,
    )
    assert is_valid
    assert error is None


def test_validate_consistency_handles_missing_parsed_strike():
    options_data = {"strikes": [100]}
    is_valid, error = StrikeValidator.validate_consistency(
        parsed_strike=None,
        data_strike=100.0,
        contract_name="test",
        index=0,
        options_data=options_data,
    )
    assert is_valid
    assert error is None


def test_validate_consistency_flags_mismatch():
    options_data = {"strikes": [100]}
    is_valid, error = StrikeValidator.validate_consistency(
        parsed_strike=100.2,
        data_strike=100.0,
        contract_name="test",
        index=0,
        options_data=options_data,
    )
    assert not is_valid
    assert "Strike mismatch" in error
