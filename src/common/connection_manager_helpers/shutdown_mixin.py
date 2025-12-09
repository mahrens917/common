"""Shared shutdown request helper for connection manager components."""

from __future__ import annotations


class ShutdownRequestMixin:
    """Provide a common shutdown flag setter."""

    def request_shutdown(self) -> None:
        """Mark component for graceful shutdown."""
        self._shutdown_requested = True
