from common.redis_protocol.kalshi_store.reader_helpers import aggregator_utils
from common.value_coercion import string_or_else, to_optional_float


def test_build_strike_summary_preserves_order():
    grouped = {("2025-01-01", 1.0, "call"): ["TK1"], ("2025-01-01", 2.0, "call"): ["TK2"]}
    market_by_ticker = {
        "TK1": {"floor_strike": "0.1", "cap_strike": "0.2", "event_type": "E", "event_ticker": "T"},
        "TK2": {"floor_strike": "1.1", "cap_strike": None, "event_type": "", "event_ticker": ""},
    }

    summary = aggregator_utils.build_strike_summary(grouped, market_by_ticker)
    assert "2025-01-01" in summary
    assert summary["2025-01-01"][0]["strike"] == 1.0
    assert isinstance(summary["2025-01-01"][0]["floor_strike"], float)


def test_coercion_helpers_delegation():
    assert string_or_else(None, otherwise="X") == "X"
    assert string_or_else(b"abc") == "abc"
    assert to_optional_float("2.5", context="ctx") == 2.5
