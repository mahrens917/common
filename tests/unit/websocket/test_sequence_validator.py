import logging

import pytest

from src.common.websocket.sequence_validator import SequenceValidator
from src.common.websocket.sequence_validator_helpers.sequence_checker import SequenceGapError

_TEST_COUNT_2 = 2


def test_sequence_validator_initializes_new_sid():
    validator = SequenceValidator("kalshi")
    is_valid, gap = validator.validate_sequence(1, 100)
    assert is_valid is True
    assert gap is None


def test_sequence_validator_accepts_contiguous_sequence():
    validator = SequenceValidator("kalshi")
    validator.validate_sequence(1, 10)
    is_valid, gap = validator.validate_sequence(1, 11)
    assert is_valid is True
    assert gap is None


def test_sequence_validator_detects_gap_within_tolerance():
    validator = SequenceValidator("kalshi", max_gap_tolerance=5)
    validator.validate_sequence(1, 10)
    is_valid, gap = validator.validate_sequence(1, 13)
    assert is_valid is False
    assert gap == _TEST_COUNT_2


def test_sequence_validator_raises_when_gap_exceeds_tolerance():
    validator = SequenceValidator("kalshi", max_gap_tolerance=1)
    validator.validate_sequence(1, 10)

    with pytest.raises(SequenceGapError):
        validator.validate_sequence(1, 13)


def test_sequence_validator_detects_duplicates():
    validator = SequenceValidator("kalshi")
    validator.validate_sequence(1, 10)
    is_valid, gap = validator.validate_sequence(1, 10)
    assert is_valid is False
    assert gap is None


def test_sequence_validator_reset_operations():
    validator = SequenceValidator("kalshi")
    validator.validate_sequence(1, 10)
    validator.validate_sequence(2, 20)
    validator.reset_sid(1)
    assert 1 not in validator.sid_to_last_seq

    validator.reset_all()
    assert not validator.sid_to_last_seq
    assert not validator.sid_to_gap_count


def test_sequence_validator_stats_and_logging(caplog):
    caplog.set_level(logging.INFO)
    validator = SequenceValidator("kalshi")
    validator.validate_sequence(1, 10)
    validator.validate_sequence(1, 13)

    stats = validator.get_stats()
    assert stats["total_sids"] == 1
    assert stats["total_gaps"] == _TEST_COUNT_2

    validator.log_stats()
    assert any("sequence stats" in record.message for record in caplog.records)
