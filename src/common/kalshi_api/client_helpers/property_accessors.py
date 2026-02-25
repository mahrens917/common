"""Property accessor helpers for KalshiClient dynamic binding."""

from __future__ import annotations

from typing import Any, Optional


def get_session_lock(client):
    """Get the session lock from the session manager or cache."""
    manager = getattr(client, "_session_manager", None)
    if manager is not None:
        lock = manager.session_lock
        client.__dict__["_cached_session_lock"] = lock
        return lock
    return client.__dict__.get("_cached_session_lock", None)


def set_session_lock(client, value) -> None:
    """Set the session lock on both the manager and cache."""
    manager = getattr(client, "_session_manager", None)
    if manager is None:
        client.__dict__["_cached_session_lock"] = value
        return
    manager.set_session_lock(value)
    client.__dict__["_cached_session_lock"] = value


def get_initialized(client) -> bool:
    """Get the initialized state of the client."""
    initialized = client.__dict__.get("_initialized", None)
    result = False
    if initialized is not None:
        result = bool(initialized)
    return result


def set_initialized(client, value: bool) -> None:
    """Set the initialized state of the client."""
    setattr(client, "_initialized", value)


def get_trade_store(client) -> Optional[Any]:
    """Get the trade store from the client."""
    return client.__dict__.get("_trade_store", None)


def set_trade_store(client, value: Optional[Any]) -> None:
    """Set the trade store on the client."""
    setattr(client, "_trade_store", value)
