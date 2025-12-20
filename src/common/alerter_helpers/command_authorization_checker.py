"""Command authorization checking for Telegram users."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_TELEGRAM_MESSAGE_TEXT = ""
DEFAULT_TELEGRAM_ID_STR = ""
DEFAULT_TELEGRAM_FIRST_NAME = ""
DEFAULT_TELEGRAM_LAST_NAME = ""


class CommandAuthorizationChecker:
    """Checks if Telegram users are authorized to execute commands."""

    def __init__(self, authorized_user_ids: List[str]):
        """
        Initialize authorization checker.

        Args:
            authorized_user_ids: List of authorized user IDs/usernames
        """
        self.authorized_user_ids = authorized_user_ids

    def _extract_user_field(self, user_info: dict, field: str, substitute: str) -> str:
        """Extract and validate a user info field."""
        value = user_info.get(field)
        if field == "id":
            return str(value) if value is not None else substitute
        return value if isinstance(value, str) else substitute

    def _extract_user_info(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Extract user information from Telegram message."""
        user_info = message.get("from")
        if not isinstance(user_info, dict):
            user_info = {}

        return {
            "username": self._extract_user_field(user_info, "username", DEFAULT_TELEGRAM_MESSAGE_TEXT),
            "user_id": self._extract_user_field(user_info, "id", DEFAULT_TELEGRAM_ID_STR),
            "first_name": self._extract_user_field(user_info, "first_name", DEFAULT_TELEGRAM_FIRST_NAME),
            "last_name": self._extract_user_field(user_info, "last_name", DEFAULT_TELEGRAM_LAST_NAME),
        }

    def _check_authorization(self, user_data: Dict[str, str], authorized_users: List[str]) -> bool:
        """Check if user is authorized by username or ID."""
        username = user_data["username"]
        user_id = user_data["user_id"]

        if username and username in authorized_users:
            logger.info(f"Access granted to authorized username: {username}")
            return True

        if user_id and user_id in authorized_users:
            logger.info(f"Access granted to authorized user ID: {user_id}")
            return True

        return False

    def is_authorized_user(self, message: Dict[str, Any]) -> bool:
        """
        Check if user is authorized - RESTRICTED ACCESS ONLY.

        Args:
            message: Telegram message with user info

        Returns:
            True if authorized, False otherwise
        """
        authorized_users = [user.strip() for user in self.authorized_user_ids if user.strip()]

        # SECURITY: If no authorized users configured, DENY ALL ACCESS (fail-safe)
        if not authorized_users:
            logger.warning("No TELEGRAM_AUTHORIZED_USERS configured - denying all access for security")
            return False

        # Extract user information
        user_data = self._extract_user_info(message)

        # Log authorization attempt for security monitoring
        logger.info(
            f"Authorization attempt - Username: {user_data['username']}, ID: {user_data['user_id']}, "
            f"Name: {user_data['first_name']} {user_data['last_name']}"
        )

        # Check authorization
        if self._check_authorization(user_data, authorized_users):
            return True

        # Access denied - log for security monitoring
        logger.warning(
            f"Access DENIED to unauthorized user - Username: {user_data['username']}, "
            f"ID: {user_data['user_id']}, Name: {user_data['first_name']} {user_data['last_name']}"
        )
        return False
