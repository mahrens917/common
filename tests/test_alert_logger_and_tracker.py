import logging

import pytest

from common.memory_monitor_helpers.alert_logger import AlertLogger
from common.memory_monitor_helpers.collection_tracker import CollectionTracker


def test_alert_logger_emits_severity(caplog):
    logger = AlertLogger("svc")
    alerts = [
        {"severity": "critical", "message": "crit"},
        {"severity": "error", "message": "err"},
        {"severity": "warning", "message": "warn"},
        {"severity": "info", "message": "info"},
        {"message": "default"},  # falls back to info
    ]
    with caplog.at_level(logging.INFO):
        logger.log_alerts({"alerts": alerts})

    messages = [record.message for record in caplog.records]
    assert "crit" in "".join(messages)
    assert "err" in "".join(messages)
    assert "warn" in "".join(messages)
    assert "info" in "".join(messages)
    assert "default" in "".join(messages)


def test_collection_tracker_handles_errors(caplog):
    tracker = CollectionTracker()

    def bad_getter():
        raise ValueError("boom")

    tracker.track_collection("bad", bad_getter)
    tracker.track_collection("good", lambda: 5)

    with caplog.at_level(logging.WARNING):
        sizes = tracker.get_collection_sizes()

    assert sizes["bad"] == -1
    assert sizes["good"] == 5
    assert any("Failed to get size" in record.message for record in caplog.records)
