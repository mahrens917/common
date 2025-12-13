from __future__ import annotations

"""HTTP helper utilities shared across connection managers."""

from typing import Any, Optional
from urllib.parse import urlsplit


def is_aiohttp_session_open(session: Optional[Any]) -> bool:
    """Return True when the provided aiohttp session exists and remains open."""
    if session is None:
        _none_guard_value = False
        return _none_guard_value
    if not hasattr(session, "closed"):
        return False
    return not bool(session.closed)


def ensure_http_url(request_url: str) -> str:
    """Ensure the provided URL uses an allowed HTTP/HTTPS scheme."""
    parsed = urlsplit(request_url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {request_url}")
    if not parsed.netloc:
        raise ValueError(f"URL missing network location: {request_url}")
    return request_url


class AioHTTPSessionConnectionMixin:
    """Mixin that exposes `is_connected` based on an aiohttp session attribute."""

    session: Optional[Any]  # Expected attribute on subclasses

    def is_connected(self) -> bool:
        """Return True when the stored aiohttp session remains open."""
        session = self.session if hasattr(self, "session") else None
        return is_aiohttp_session_open(session)


__all__ = ["is_aiohttp_session_open", "ensure_http_url", "AioHTTPSessionConnectionMixin"]
