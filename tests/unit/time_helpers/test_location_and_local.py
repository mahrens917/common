from datetime import datetime, timezone
from typing import Generator, Optional

import pytest

from common.time_helpers.location import (
    TimezoneLookupError,
    _STATE,
    _set_override_finder,
    get_timezone_finder,
    get_timezone_from_coordinates,
    resolve_timezone,
    shutdown_timezone_finder,
)
from common.time_utils.local import calculate_local_midnight_utc, is_after_local_midnight


@pytest.fixture(autouse=True)
def reset_timezone_state() -> Generator[None, None, None]:
    _STATE.finder = None
    _STATE.error = None
    _set_override_finder(None)
    yield
    _STATE.finder = None
    _STATE.error = None
    _set_override_finder(None)


def test_get_timezone_from_coordinates_returns_timezone() -> None:
    class StubFinder:
        def timezone_at(self, *, lng: float, lat: float) -> str:
            return "Europe/Paris"

    _set_override_finder(StubFinder())

    tz = get_timezone_from_coordinates(48.85, 2.35)

    assert tz == "Europe/Paris"


def test_get_timezone_from_coordinates_raises_when_no_match() -> None:
    class StubFinder:
        def timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
            return None

    _set_override_finder(StubFinder())

    with pytest.raises(TimezoneLookupError, match="Unable to resolve timezone"):
        get_timezone_from_coordinates(0.0, 0.0)


def test_resolve_timezone_uses_configured_value() -> None:
    result = resolve_timezone(40.7, -74.0, configured_timezone="America/New_York")

    assert result == "America/New_York"


def test_resolve_timezone_falls_back_to_coordinates() -> None:
    class StubFinder:
        def timezone_at(self, *, lng: float, lat: float) -> str:
            return "America/Chicago"

    _set_override_finder(StubFinder())

    result = resolve_timezone(41.9, -87.6)

    assert result == "America/Chicago"


def test_shutdown_timezone_finder_invokes_close() -> None:
    closed: list[str] = []

    class StubFinder:
        def close(self) -> None:
            closed.append("close")

    _set_override_finder(StubFinder())
    shutdown_timezone_finder()

    assert closed == ["close"]


def test_local_midnight_and_after_check(monkeypatch):
    now = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)

    # Use a fixed timezone response
    monkeypatch.setattr(
        "common.time_helpers.location.get_timezone_from_coordinates",
        lambda *_args, **_kwargs: "UTC",
    )

    midnight = calculate_local_midnight_utc(0, 0, now)
    assert midnight.hour == 0 and midnight.tzinfo == timezone.utc

    assert is_after_local_midnight(0, 0, now)
    assert is_after_local_midnight(0, 0, datetime(2024, 1, 1, 0, tzinfo=timezone.utc))
