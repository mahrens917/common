"""
Canonical connection state definitions for all services.

This module provides the single source of truth for connection states
across all services to prevent circular imports and ensure consistency.
"""

from enum import Enum


class ConnectionState(Enum):
    """
    Connection states for consistent state management across all services.

    These states provide a clear progression from disconnected to fully operational,
    allowing for precise monitoring and appropriate reconnection logic.
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
