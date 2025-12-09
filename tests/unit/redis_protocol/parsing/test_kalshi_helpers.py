"""Tests for Kalshi parsing helper exports."""

from datetime import datetime, timezone

import pytest

from src.common.redis_protocol.parsing import kalshi_helpers


@pytest.mark.parametrize(
    ("func_name", "args"),
    [
        ("parse_year_month_day_format", ("token", "KXHIGH", 1, "rest")),
        ("parse_intraday_format", ("token", datetime.now(timezone.utc), 1, 1, "rest")),
        ("parse_day_month_year_format", ("token", 1, 1, "rest")),
    ],
)
def test_kalshi_helpers_delegate_to_canonical(monkeypatch, func_name, args):
    called = {}

    def fake_fn(*call_args):  # type: ignore[no-untyped-def]
        called["args"] = call_args
        return datetime(2020, 1, 1)

    monkeypatch.setattr(kalshi_helpers, func_name, fake_fn)

    result = getattr(kalshi_helpers, func_name)(*args)

    assert isinstance(result, datetime)
    assert called["args"] == args
