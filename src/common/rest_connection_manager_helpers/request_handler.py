"""Base request handler for REST connection managers."""

from __future__ import annotations

from typing import Any


class RequestHandler:
    """Base class for REST request handlers.

    Subclasses must implement handle_request.  Constructor keyword arguments
    are stored as instance attributes for use by subclass logic.
    """

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def handle_request(self) -> None:
        """Handle an incoming request.  Must be overridden by subclasses."""
        raise NotImplementedError


__all__ = ["RequestHandler"]
