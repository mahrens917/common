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


def test_build_snapshot_sides_dollar_format() -> None:
    msg_data = {
        "yes_dollars_fp": [["0.60", "3.0"], ["0.55", "1.0"]],
        "no_dollars_fp": [["0.40", "2.0"]],
    }

    sides = build_snapshot_sides(msg_data, "TEST.T")

    assert sides["yes_bids"] == {"60.0": 3.0, "55.0": 1.0}
    assert sides["yes_asks"] == {"60.0": 2.0}


def test_build_snapshot_sides_dollar_format_invalid_entry_raises() -> None:
    msg_data = {
        "yes_dollars_fp": ["bad_entry"],
    }

    with pytest.raises(DataError):
        build_snapshot_sides(msg_data, "TEST.T")


def test_build_snapshot_sides_zero_size_skipped() -> None:
    msg_data = {
        "yes": [[60, 0], [55, 2]],
    }

    sides = build_snapshot_sides(msg_data, "TEST.T")

    assert sides["yes_bids"] == {"55.0": 2.0}


def test_build_snapshot_sides_non_numeric_size_skipped() -> None:
    msg_data = {
        "yes": [[60, "bad"], [55, 1]],
    }

    sides = build_snapshot_sides(msg_data, "TEST.T")

    assert sides["yes_bids"] == {"55.0": 1.0}


def test_merge_orderbook_payload_no_msg_dict() -> None:
    with pytest.raises(ValueError):
        merge_orderbook_payload({"type": "snapshot", "msg": None})


def test_merge_orderbook_payload_no_data_section() -> None:
    msg_type, msg_data, ticker = merge_orderbook_payload({"type": "snapshot", "msg": {"market_ticker": "TEST.T"}})

    assert msg_type == "snapshot"
    assert ticker == "TEST.T"


def test_merge_orderbook_payload_bids_key() -> None:
    message = {
        "type": "snapshot",
        "msg": {"market_ticker": "TEST.T"},
        "data": {
            "bids": [[50, 1]],
        },
    }

    _, msg_data, _ = merge_orderbook_payload(message)

    assert msg_data["yes"] == [[50, 1]]
