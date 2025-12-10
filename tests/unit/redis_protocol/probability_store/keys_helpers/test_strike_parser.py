import pytest

from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError
from common.redis_protocol.probability_store.keys_helpers.strike_parser import (
    StrikeSortKeyParser,
)


class TestStrikeSortKeyParser:
    def test_parse_plain_float_success(self):
        assert StrikeSortKeyParser.parse_plain_float("100.5") == (0, 100.5)
        assert StrikeSortKeyParser.parse_plain_float("100") == (0, 100.0)

    def test_parse_plain_float_failure(self):
        with pytest.raises(ProbabilityStoreError, match="Invalid strike key"):
            StrikeSortKeyParser.parse_plain_float("abc")

    def test_parse_greater_than_success(self):
        assert StrikeSortKeyParser.parse_greater_than(">100.5") == (1, 100.5)

    def test_parse_greater_than_failure(self):
        with pytest.raises(ProbabilityStoreError, match="Invalid strike key"):
            StrikeSortKeyParser.parse_greater_than(">abc")

    def test_parse_less_than_success(self):
        assert StrikeSortKeyParser.parse_less_than("<100.5") == (-1, 100.5)

    def test_parse_less_than_failure(self):
        with pytest.raises(ProbabilityStoreError, match="Invalid strike key"):
            StrikeSortKeyParser.parse_less_than("<abc")

    def test_parse_range_success(self):
        assert StrikeSortKeyParser.parse_range("100-200") == (0, 100.0)
        assert StrikeSortKeyParser.parse_range("100.5-200.5") == (0, 100.5)

    def test_parse_range_failure(self):
        with pytest.raises(ProbabilityStoreError, match="Invalid strike range"):
            StrikeSortKeyParser.parse_range("abc-def")
