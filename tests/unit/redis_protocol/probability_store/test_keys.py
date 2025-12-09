from datetime import datetime

import pytest

from src.common.redis_protocol.probability_store.exceptions import ProbabilityStoreError
from src.common.redis_protocol.probability_store.keys import (
    expiry_sort_key,
    parse_probability_key,
    strike_sort_key,
)


class TestKeys:
    def test_strike_sort_key_numeric(self):
        assert strike_sort_key("100.5") == (0, 100.5)
        assert strike_sort_key("50") == (0, 50.0)

    def test_strike_sort_key_prefixed(self):
        assert strike_sort_key(">100") == (1, 100.0)
        assert strike_sort_key("<50") == (-1, 50.0)

    def test_strike_sort_key_range(self):
        assert strike_sort_key("10-20") == (0, 10.0)

    def test_strike_sort_key_invalid_prefix(self):
        with pytest.raises(ProbabilityStoreError, match="Invalid strike key"):
            strike_sort_key(">abc")

    def test_strike_sort_key_invalid_range(self):
        with pytest.raises(ProbabilityStoreError, match="Invalid strike range"):
            strike_sort_key("abc-def")

    def test_strike_sort_key_unsupported(self):
        with pytest.raises(ProbabilityStoreError, match="Unsupported strike key"):
            strike_sort_key("invalid")

    def test_expiry_sort_key_datetime(self):
        key = "2023-01-01T12:00:00Z"
        expected = datetime.fromisoformat("2023-01-01T12:00:00+00:00")
        assert expiry_sort_key(key) == expected

    def test_expiry_sort_key_string(self):
        assert expiry_sort_key("daily") == "daily"

    def test_parse_probability_key_standard(self):
        # standard 5 parts: prefix:currency:expiry:strike_type:strike
        key = "prob:BTC:2023-01-01:call:100"
        assert parse_probability_key(key) == ("2023-01-01", "call", "100")

    def test_parse_probability_key_long_expiry(self):
        # expiry with colons? maybe not standard but handled
        # prefix:currency:exp:iry:part:strike_type:strike
        key = "prob:BTC:2023:01:01:call:100"
        assert parse_probability_key(key) == ("2023:01:01", "call", "100")

    def test_parse_probability_key_invalid_length(self):
        with pytest.raises(ProbabilityStoreError, match="Invalid probability key format"):
            parse_probability_key("prob:BTC:expiry:strike")

    def test_parse_probability_key_empty_expiry(self):
        # Case where expiry part is empty but length is sufficient?
        # prob:BTC::call:100
        with pytest.raises(ProbabilityStoreError, match="Could not extract expiry"):
            parse_probability_key("prob:BTC::call:100")
