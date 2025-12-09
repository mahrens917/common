"""Tests for common utils http_helpers module."""

from __future__ import annotations

import pytest

from src.common.utils.http_helpers import build_http_session


class TestBuildHttpSession:
    """Tests for build_http_session function."""

    async def test_creates_session_with_timeout(self) -> None:
        """Session has correct timeout configured."""
        session = build_http_session(
            timeout_seconds=30.0,
            user_agent="TestClient/1.0",
        )
        try:
            assert session.timeout.total == 30.0
        finally:
            await session.close()

    async def test_creates_session_with_user_agent(self) -> None:
        """Session has correct user agent header."""
        session = build_http_session(
            timeout_seconds=30.0,
            user_agent="TestClient/1.0",
        )
        try:
            assert session.headers.get("User-Agent") == "TestClient/1.0"
        finally:
            await session.close()

    async def test_creates_session_with_additional_headers(self) -> None:
        """Session includes additional headers."""
        session = build_http_session(
            timeout_seconds=30.0,
            user_agent="TestClient/1.0",
            additional_headers={"Accept": "application/json"},
        )
        try:
            assert session.headers.get("Accept") == "application/json"
            assert session.headers.get("User-Agent") == "TestClient/1.0"
        finally:
            await session.close()

    async def test_creates_session_without_additional_headers(self) -> None:
        """Session works without additional headers."""
        session = build_http_session(
            timeout_seconds=30.0,
            user_agent="TestClient/1.0",
            additional_headers=None,
        )
        try:
            assert session.headers.get("User-Agent") == "TestClient/1.0"
        finally:
            await session.close()

    async def test_additional_headers_override_default(self) -> None:
        """Additional headers can override User-Agent."""
        session = build_http_session(
            timeout_seconds=30.0,
            user_agent="TestClient/1.0",
            additional_headers={"User-Agent": "OverrideClient/2.0"},
        )
        try:
            assert session.headers.get("User-Agent") == "OverrideClient/2.0"
        finally:
            await session.close()

    def test_module_exports(self) -> None:
        """Module exports build_http_session in __all__."""
        from src.common.utils import http_helpers

        assert "build_http_session" in http_helpers.__all__
