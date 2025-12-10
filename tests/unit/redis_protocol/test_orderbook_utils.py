from __future__ import annotations

import pytest

from common.exceptions import DataError, ValidationError
from common.redis_protocol.orderbook_utils import build_snapshot_sides, merge_orderbook_payload

_TEST_COUNT_3 = 3


def test_merge_orderbook_payload_merges_nested_sections() -> None:
    message = {
        "type": "orderbook_snapshot",
        "msg": {"market_ticker": "TEST.T"},
        "data": {
            "orderbook": {"timestamp": "123"},
            "levels": {"depth": 3},
            "yes": [[60, 4]],
            "asks": [[40, 5]],
        },
    }

    msg_type, msg_data, ticker = merge_orderbook_payload(message)

    assert msg_type == "orderbook_snapshot"
    assert ticker == "TEST.T"
    assert msg_data["timestamp"] == "123"
    assert msg_data["depth"] == _TEST_COUNT_3
    assert "yes" in msg_data and "no" in msg_data


def test_merge_orderbook_payload_missing_ticker_raises() -> None:
    with pytest.raises(ValueError):
        merge_orderbook_payload({"type": "orderbook_snapshot", "msg": {}})


def test_build_snapshot_sides_converts_levels() -> None:
    msg_data = {
        "yes": [[60, 3], [55, 1]],
        "no": [[40, 2]],
    }

    sides = build_snapshot_sides(msg_data, "TEST.T")

    assert sides["yes_bids"] == {"60.0": 3.0, "55.0": 1.0}
    assert sides["yes_asks"] == {"60.0": 2.0}


def test_build_snapshot_sides_invalid_level_raises() -> None:
    with pytest.raises(DataError):
        build_snapshot_sides({"yes": [[60]]}, "TEST.T")
