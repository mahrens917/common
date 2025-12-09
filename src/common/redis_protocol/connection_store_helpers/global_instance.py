"""
Global instance management for ConnectionStore
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..connection_store import ConnectionStore

_connection_store: Optional["ConnectionStore"] = None


async def get_connection_store() -> "ConnectionStore":
    """
    Get the global connection store instance.

    Returns:
        Initialized ConnectionStore instance
    """
    global _connection_store

    if _connection_store is None:
        from ..connection_store import ConnectionStore

        _connection_store = ConnectionStore()
        await _connection_store.initialize()

    return _connection_store
