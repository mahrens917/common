"""Tests for alerter_helpers.command_authorization_checker module."""

import pytest

from common.alerter_helpers.command_authorization_checker import (
    DEFAULT_TELEGRAM_FIRST_NAME,
    DEFAULT_TELEGRAM_ID_STR,
    DEFAULT_TELEGRAM_LAST_NAME,
    DEFAULT_TELEGRAM_MESSAGE_TEXT,
    CommandAuthorizationChecker,
)


class TestConstants:
    """Tests for module constants."""

    def test_default_message_text(self) -> None:
        """Test DEFAULT_TELEGRAM_MESSAGE_TEXT is empty."""
        assert DEFAULT_TELEGRAM_MESSAGE_TEXT == ""

    def test_default_id_str(self) -> None:
        """Test DEFAULT_TELEGRAM_ID_STR is empty."""
        assert DEFAULT_TELEGRAM_ID_STR == ""

    def test_default_first_name(self) -> None:
        """Test DEFAULT_TELEGRAM_FIRST_NAME is empty."""
        assert DEFAULT_TELEGRAM_FIRST_NAME == ""

    def test_default_last_name(self) -> None:
        """Test DEFAULT_TELEGRAM_LAST_NAME is empty."""
        assert DEFAULT_TELEGRAM_LAST_NAME == ""


class TestCommandAuthorizationCheckerInit:
    """Tests for CommandAuthorizationChecker initialization."""

    def test_stores_authorized_user_ids(self) -> None:
        """Test initialization stores authorized user IDs."""
        user_ids = ["user1", "user2"]
        checker = CommandAuthorizationChecker(user_ids)

        assert checker.authorized_user_ids == user_ids


class TestExtractUserField:
    """Tests for _extract_user_field method."""

    def test_extracts_id_field(self) -> None:
        """Test extracts ID field as string."""
        checker = CommandAuthorizationChecker([])
        user_info = {"id": 12345}

        result = checker._extract_user_field(user_info, "id", "default")

        assert result == "12345"

    def test_extracts_string_field(self) -> None:
        """Test extracts string field."""
        checker = CommandAuthorizationChecker([])
        user_info = {"username": "testuser"}

        result = checker._extract_user_field(user_info, "username", "default")

        assert result == "testuser"

    def test_returns_substitute_for_none_id(self) -> None:
        """Test returns substitute for None ID."""
        checker = CommandAuthorizationChecker([])
        user_info = {"id": None}

        result = checker._extract_user_field(user_info, "id", "default")

        assert result == "default"

    def test_returns_substitute_for_non_string(self) -> None:
        """Test returns substitute for non-string value."""
        checker = CommandAuthorizationChecker([])
        user_info = {"username": 12345}  # Not a string

        result = checker._extract_user_field(user_info, "username", "default")

        assert result == "default"

    def test_returns_substitute_for_missing_field(self) -> None:
        """Test returns substitute for missing field."""
        checker = CommandAuthorizationChecker([])
        user_info: dict = {}

        result = checker._extract_user_field(user_info, "username", "default")

        assert result == "default"


class TestExtractUserInfo:
    """Tests for _extract_user_info method."""

    def test_extracts_all_fields(self) -> None:
        """Test extracts all user info fields."""
        checker = CommandAuthorizationChecker([])
        message = {
            "from": {
                "id": 12345,
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
            }
        }

        result = checker._extract_user_info(message)

        assert result["user_id"] == "12345"
        assert result["username"] == "testuser"
        assert result["first_name"] == "Test"
        assert result["last_name"] == "User"

    def test_handles_missing_from(self) -> None:
        """Test handles missing 'from' field."""
        checker = CommandAuthorizationChecker([])
        message: dict = {}

        result = checker._extract_user_info(message)

        assert result["user_id"] == ""
        assert result["username"] == ""
        assert result["first_name"] == ""
        assert result["last_name"] == ""

    def test_handles_non_dict_from(self) -> None:
        """Test handles non-dict 'from' field."""
        checker = CommandAuthorizationChecker([])
        message = {"from": "not_a_dict"}

        result = checker._extract_user_info(message)

        assert result["user_id"] == ""
        assert result["username"] == ""


class TestCheckAuthorization:
    """Tests for _check_authorization method."""

    def test_authorizes_by_username(self) -> None:
        """Test authorizes by username."""
        checker = CommandAuthorizationChecker([])
        user_data = {"username": "testuser", "user_id": "12345"}
        authorized_users = ["testuser"]

        result = checker._check_authorization(user_data, authorized_users)

        assert result is True

    def test_authorizes_by_user_id(self) -> None:
        """Test authorizes by user ID."""
        checker = CommandAuthorizationChecker([])
        user_data = {"username": "", "user_id": "12345"}
        authorized_users = ["12345"]

        result = checker._check_authorization(user_data, authorized_users)

        assert result is True

    def test_denies_unauthorized_user(self) -> None:
        """Test denies unauthorized user."""
        checker = CommandAuthorizationChecker([])
        user_data = {"username": "unknown", "user_id": "99999"}
        authorized_users = ["testuser", "12345"]

        result = checker._check_authorization(user_data, authorized_users)

        assert result is False

    def test_denies_empty_username_and_id(self) -> None:
        """Test denies when username and ID are empty."""
        checker = CommandAuthorizationChecker([])
        user_data = {"username": "", "user_id": ""}
        authorized_users = ["testuser"]

        result = checker._check_authorization(user_data, authorized_users)

        assert result is False


class TestIsAuthorizedUser:
    """Tests for is_authorized_user method."""

    def test_authorizes_valid_user(self) -> None:
        """Test authorizes valid user."""
        checker = CommandAuthorizationChecker(["testuser", "12345"])
        message = {"from": {"id": 12345, "username": "testuser"}}

        result = checker.is_authorized_user(message)

        assert result is True

    def test_authorizes_by_id_only(self) -> None:
        """Test authorizes by ID when username not in list."""
        checker = CommandAuthorizationChecker(["12345"])
        message = {"from": {"id": 12345, "username": "unknown"}}

        result = checker.is_authorized_user(message)

        assert result is True

    def test_denies_when_no_authorized_users(self) -> None:
        """Test denies when no authorized users configured."""
        checker = CommandAuthorizationChecker([])
        message = {"from": {"id": 12345, "username": "testuser"}}

        result = checker.is_authorized_user(message)

        assert result is False

    def test_denies_when_only_whitespace_users(self) -> None:
        """Test denies when authorized users are only whitespace."""
        checker = CommandAuthorizationChecker(["  ", ""])
        message = {"from": {"id": 12345, "username": "testuser"}}

        result = checker.is_authorized_user(message)

        assert result is False

    def test_denies_unauthorized_user(self) -> None:
        """Test denies unauthorized user."""
        checker = CommandAuthorizationChecker(["admin", "99999"])
        message = {"from": {"id": 12345, "username": "hacker"}}

        result = checker.is_authorized_user(message)

        assert result is False

    def test_strips_whitespace_from_authorized_users(self) -> None:
        """Test strips whitespace from authorized user IDs."""
        checker = CommandAuthorizationChecker(["  testuser  ", " 12345 "])
        message = {"from": {"id": 12345, "username": "testuser"}}

        result = checker.is_authorized_user(message)

        assert result is True
