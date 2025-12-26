"""Tests for alerter_helpers.unauthorized_command_handler module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.alerter_helpers.unauthorized_command_handler import (
    DEFAULT_TELEGRAM_FIRST_NAME,
    DEFAULT_TELEGRAM_LAST_NAME,
    UNKNOWN_TELEGRAM_USER_ID,
    UNKNOWN_TELEGRAM_USERNAME,
    UnauthorizedCommandHandler,
)
from common.alerting import AlertSeverity


class TestUnauthorizedCommandHandlerInit:
    """Tests for UnauthorizedCommandHandler initialization."""

    def test_stores_callback(self) -> None:
        """Test stores send_alert_callback."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        assert handler.send_alert_callback is mock_callback


class TestUnauthorizedCommandHandlerHandleUnauthorizedAttempt:
    """Tests for handle_unauthorized_attempt method."""

    @pytest.mark.asyncio
    async def test_sends_security_alert(self) -> None:
        """Test sends security alert with correct severity."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {
            "from": {
                "username": "hacker",
                "id": 12345,
                "first_name": "Evil",
                "last_name": "Person",
            }
        }

        await handler.handle_unauthorized_attempt("shutdown", message)

        mock_callback.assert_called_once()
        call_args = mock_callback.call_args
        assert call_args[1]["alert_type"] == "security_breach"
        assert call_args[0][1] == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_includes_user_info_in_alert(self) -> None:
        """Test includes user information in alert."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {
            "from": {
                "username": "attacker",
                "id": 99999,
                "first_name": "John",
                "last_name": "Doe",
            }
        }

        await handler.handle_unauthorized_attempt("restart", message)

        alert_text = mock_callback.call_args[0][0]
        assert "@attacker" in alert_text
        assert "99999" in alert_text
        assert "John Doe" in alert_text
        assert "/restart" in alert_text

    @pytest.mark.asyncio
    async def test_handles_missing_user_info(self) -> None:
        """Test handles missing user info with defaults."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {}  # No "from" key

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert f"@{UNKNOWN_TELEGRAM_USERNAME}" in alert_text
        assert UNKNOWN_TELEGRAM_USER_ID in alert_text

    @pytest.mark.asyncio
    async def test_handles_missing_username(self) -> None:
        """Test handles missing username."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"id": 12345}}

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert f"@{UNKNOWN_TELEGRAM_USERNAME}" in alert_text
        assert "12345" in alert_text

    @pytest.mark.asyncio
    async def test_handles_empty_username(self) -> None:
        """Test handles empty username string."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "", "id": 12345}}

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert f"@{UNKNOWN_TELEGRAM_USERNAME}" in alert_text

    @pytest.mark.asyncio
    async def test_handles_missing_user_id(self) -> None:
        """Test handles missing user id."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "testuser"}}

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert "@testuser" in alert_text
        assert UNKNOWN_TELEGRAM_USER_ID in alert_text

    @pytest.mark.asyncio
    async def test_handles_non_dict_user_info(self) -> None:
        """Test handles non-dict user info."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": "invalid"}  # Not a dict

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert f"@{UNKNOWN_TELEGRAM_USERNAME}" in alert_text

    @pytest.mark.asyncio
    async def test_handles_missing_names(self) -> None:
        """Test handles missing first/last names."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "testuser", "id": 12345}}

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        # Full name should be empty or minimal
        assert "👤 User:" in alert_text

    @pytest.mark.asyncio
    async def test_handles_first_name_only(self) -> None:
        """Test handles first name only."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "testuser", "id": 12345, "first_name": "John"}}

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert "John" in alert_text

    @pytest.mark.asyncio
    async def test_handles_last_name_only(self) -> None:
        """Test handles last name only."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "testuser", "id": 12345, "last_name": "Doe"}}

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert "Doe" in alert_text

    @pytest.mark.asyncio
    async def test_handles_non_string_names(self) -> None:
        """Test handles non-string name values."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "testuser", "id": 12345, "first_name": 123, "last_name": None}}

        await handler.handle_unauthorized_attempt("test", message)

        # Should not raise
        mock_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_includes_timestamp(self) -> None:
        """Test includes timestamp in alert."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "testuser", "id": 12345}}

        await handler.handle_unauthorized_attempt("test", message)

        alert_text = mock_callback.call_args[0][0]
        assert "⏰ Time:" in alert_text

    @pytest.mark.asyncio
    async def test_alert_contains_all_sections(self) -> None:
        """Test alert contains all expected sections."""
        mock_callback = AsyncMock()
        handler = UnauthorizedCommandHandler(mock_callback)

        message = {"from": {"username": "testuser", "id": 12345, "first_name": "Test"}}

        await handler.handle_unauthorized_attempt("secret", message)

        alert_text = mock_callback.call_args[0][0]
        assert "UNAUTHORIZED TELEGRAM ACCESS ATTEMPT" in alert_text
        assert "👤 User:" in alert_text
        assert "🆔 Username:" in alert_text
        assert "🔢 User ID:" in alert_text
        assert "💬 Command:" in alert_text
        assert "⏰ Time:" in alert_text


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_unknown_username_constant(self) -> None:
        """Test UNKNOWN_TELEGRAM_USERNAME constant."""
        assert UNKNOWN_TELEGRAM_USERNAME == "unknown"

    def test_unknown_user_id_constant(self) -> None:
        """Test UNKNOWN_TELEGRAM_USER_ID constant."""
        assert UNKNOWN_TELEGRAM_USER_ID == "unknown"

    def test_default_first_name_constant(self) -> None:
        """Test DEFAULT_TELEGRAM_FIRST_NAME constant."""
        assert DEFAULT_TELEGRAM_FIRST_NAME == ""

    def test_default_last_name_constant(self) -> None:
        """Test DEFAULT_TELEGRAM_LAST_NAME constant."""
        assert DEFAULT_TELEGRAM_LAST_NAME == ""
