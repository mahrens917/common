from datetime import datetime, timedelta, timezone

import pytest

from src.common.redis_protocol.market_cleanup_helpers.cleanup_helpers.expiration_checker import (
    extract_expiration_time,
    is_expired_deribit,
    is_expired_kalshi,
)


def test_is_expired_kalshi_and_deribit(caplog):
    recent_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert is_expired_kalshi(recent_time, grace_period_days=1) is False

    past_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    assert is_expired_kalshi(past_time, grace_period_days=1) is True

    with caplog.at_level("WARNING"):
        assert is_expired_kalshi("bad", grace_period_days=1) is False
        assert is_expired_deribit("also-bad", grace_period_days=1) is False
    assert "Failed to parse Kalshi expiration time" in caplog.text
    assert "Failed to parse Deribit expiry date" in caplog.text

    future_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
    past_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    assert is_expired_deribit(future_date, grace_period_days=0) is False
    assert is_expired_deribit(past_date, grace_period_days=0) is True


def test_extract_expiration_time():
    assert extract_expiration_time({}) is None
    assert extract_expiration_time({"latest_expiration_time": b"2024"}) == "2024"
    assert extract_expiration_time({b"latest_expiration_time": b"2025"}) == "2025"
