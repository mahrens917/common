"""Tests for iterable helper utilities."""

from common.utils.itertools_helpers import chunk


def test_chunk_splits_sequence_evenly():
    result = list(chunk([1, 2, 3, 4], 2))
    assert result == [[1, 2], [3, 4]]


def test_chunk_handles_remainder():
    result = list(chunk([1, 2, 3], 2))
    assert result == [[1, 2], [3]]


def test_chunk_uses_whole_list_when_size_larger():
    result = list(chunk([1, 2], 10))
    assert result == [[1, 2]]
