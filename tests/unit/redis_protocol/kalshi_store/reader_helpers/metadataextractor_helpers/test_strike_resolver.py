from __future__ import annotations

from typing import Any, Dict

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.strike_resolver import (
    StrikeResolver,
)


def _string_converter(value: Any) -> str:
    return str(value)


def test_resolve_market_strike_returns_calculated_midpoint():
    metadata: Dict[str, Any] = {
        "strike_type": "between",
        "floor_strike": "10",
        "cap_strike": "20",
    }

    result = StrikeResolver.resolve_market_strike(metadata, _string_converter)
    assert result == pytest.approx(15.0)


def test_resolve_market_strike_falls_back_to_floor_or_cap():
    floor_only: Dict[str, Any] = {
        "strike_type": "unknown",
        "floor_strike": "5",
        "cap_strike": "10",
    }
    assert StrikeResolver.resolve_market_strike(floor_only, _string_converter) == pytest.approx(5.0)

    cap_only: Dict[str, Any] = {
        "strike_type": "unknown",
        "floor_strike": None,
        "cap_strike": "8",
    }
    assert StrikeResolver.resolve_market_strike(cap_only, _string_converter) == pytest.approx(8.0)


def test_resolve_market_strike_returns_none_without_type():
    assert StrikeResolver.resolve_market_strike({}, _string_converter) is None


def test_resolve_market_strike_applies_converter():
    events: list[Any] = []

    def converter(value: Any) -> str:
        events.append(value)
        return str(value).upper()

    metadata: Dict[str, Any] = {
        "strike_type": "less",
        "cap_strike": "22",
    }

    resolved = StrikeResolver.resolve_market_strike(metadata, converter)
    assert resolved == pytest.approx(22.0)
    assert events == ["less"]


def test_resolve_strike_from_combined_delegates_to_market():
    metadata = {
        "strike_type": "greater",
        "floor_strike": "99",
    }
    assert StrikeResolver.resolve_strike_from_combined(metadata, _string_converter) == pytest.approx(99.0)
