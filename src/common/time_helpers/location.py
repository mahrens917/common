"""
Shared utilities for lazy-loading and managing TimezoneFinder instances.

This module provides a process-wide singleton TimezoneFinder instance with
lazy initialization, error caching, and test override support.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Protocol, cast

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - import used for type checking only
    from timezonefinder import TimezoneFinder as _TimezoneFinderType
else:  # pragma: no cover - runtime type alias
    _TimezoneFinderType = Any  # type: ignore[assignment]


_DEPENDENCY_MESSAGE = (
    "timezonefinder is not available; install the dependency to resolve timezones. "
    "Install it with `python -m pip install timezonefinder`."
)
_INITIALIZE_FAILURE_MESSAGE = "unable to initialise timezonefinder; check that the package is properly installed"


@dataclass
class _FinderState:
    """Cached state for the process-wide TimezoneFinder instance."""

    finder: Optional[_TimezoneFinderType] = None
    error: Optional[Exception] = None


_STATE = _FinderState()
_TIMEZONE_FINDER: Optional[_TimezoneFinderType] = None


class TimezoneLookupError(RuntimeError):
    """Raised when a timezone cannot be resolved for the provided coordinates."""


class _TimezoneFinderProtocol(Protocol):
    """Subset of timezone lookup behaviour required by callers."""

    def timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """Return timezone identifier for the provided coordinates."""
        del lng, lat
        raise NotImplementedError


def _get_override_finder() -> Optional[_TimezoneFinderType]:
    """Return a timezone finder injected via globals() for testing."""
    return cast(Optional[_TimezoneFinderType], globals().get("_TIMEZONE_FINDER"))


def _set_override_finder(value: Optional[_TimezoneFinderType]) -> None:
    """Update the override finder used by tests."""
    globals()["_TIMEZONE_FINDER"] = value


def get_timezone_finder() -> _TimezoneFinderProtocol:
    """
    Return a cached timezone finder instance, loading it on first use.

    Raises:
        TimezoneLookupError: When timezonefinder is not installed or fails to initialize.

    Returns:
        TimezoneFinder instance configured with in_memory=True.
    """
    override = _get_override_finder()
    if override is not None:
        _STATE.finder = override
        return override

    if _STATE.finder is not None:
        return _STATE.finder

    if _STATE.error is not None:
        raise TimezoneLookupError(_DEPENDENCY_MESSAGE) from _STATE.error

    try:
        import timezonefinder as timezone_module

        finder_cls = cast(type[_TimezoneFinderType], timezone_module.TimezoneFinder)
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency missing
        _STATE.error = exc
        logger.warning(
            "timezonefinder import failed; timezone lookups disabled",
            exc_info=True,
        )
        raise TimezoneLookupError(_DEPENDENCY_MESSAGE) from exc
    except AttributeError as exc:  # pragma: no cover - defensive
        _STATE.error = exc
        logger.error(
            "timezonefinder module does not provide TimezoneFinder class",
            exc_info=True,
        )
        raise TimezoneLookupError(_DEPENDENCY_MESSAGE) from exc

    try:
        _STATE.finder = finder_cls(in_memory=True)
    except (OSError, RuntimeError, ValueError) as exc:  # pragma: no cover - defensive
        _STATE.error = exc
        logger.exception("failed to initialise TimezoneFinder")
        raise TimezoneLookupError(_INITIALIZE_FAILURE_MESSAGE) from exc

    return _STATE.finder


def get_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """
    Derive an IANA timezone name from latitude and longitude.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.

    Returns:
        IANA timezone identifier string (e.g., "America/New_York").

    Raises:
        TimezoneLookupError: When timezone cannot be resolved for the coordinates.
    """
    timezone_finder = get_timezone_finder()

    tz_name = timezone_finder.timezone_at(lat=latitude, lng=longitude)
    if tz_name:
        return tz_name

    message = "Unable to resolve timezone for coordinates " f"lat={latitude:.4f} lon={longitude:.4f}; update station metadata"
    logger.error(message)
    raise TimezoneLookupError(message)


def resolve_timezone(
    latitude: float,
    longitude: float,
    configured_timezone: Optional[str] = None,
) -> str:
    """
    Resolve timezone using configured value or coordinate lookup.

    This canonical implementation supports the common pattern of checking
    for an explicitly configured timezone before using automatic
    coordinate-based lookup.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        configured_timezone: Optional pre-configured timezone name to use.
            If provided and non-empty, returned without coordinate lookup.

    Returns:
        IANA timezone identifier string (e.g., "America/New_York").

    Raises:
        TimezoneLookupError: When coordinate lookup fails.

    Example:
        >>> # Use configured timezone
        >>> resolve_timezone(40.7, -74.0, "America/New_York")
        'America/New_York'
        >>> # Coordinate lookup when no configured timezone
        >>> resolve_timezone(40.7, -74.0)
        'America/New_York'
    """
    if configured_timezone:
        return str(configured_timezone)
    return get_timezone_from_coordinates(latitude, longitude)


def shutdown_timezone_finder() -> None:
    """Release resources held by the process-wide TimezoneFinder instance."""
    attempted = False
    candidates = (
        ("state", _STATE.finder),
        ("override", _get_override_finder()),
    )

    for source, finder in candidates:
        if finder is None:
            continue

        attempted = True
        override_match = finder is _get_override_finder()
        close_candidate = getattr(finder, "close", None)
        if close_candidate is None:
            logger.debug("TimezoneFinder.close() not available; skipping shutdown.")
            continue

        if not callable(close_candidate):
            logger.warning("TimezoneFinder.close attribute exists but is not callable; skipping shutdown.")
            continue

        close_candidate()
        if source == "state":
            _STATE.finder = None
            if override_match:
                _set_override_finder(None)
        else:
            _set_override_finder(None)
        return

    if not attempted:
        logger.debug("TimezoneFinder not initialized; nothing to shut down.")


__all__ = [
    "TimezoneLookupError",
    "get_timezone_finder",
    "get_timezone_from_coordinates",
    "resolve_timezone",
    "shutdown_timezone_finder",
]
