"""Handle unauthorized Telegram command attempts."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from ..alerting import AlertSeverity

logger = logging.getLogger(__name__)

UNKNOWN_TELEGRAM_USERNAME = "unknown"
UNKNOWN_TELEGRAM_USER_ID = "unknown"
DEFAULT_TELEGRAM_FIRST_NAME = ""
DEFAULT_TELEGRAM_LAST_NAME = ""


class UnauthorizedCommandHandler:
    """Handles unauthorized Telegram command attempts with security alerts."""

    def __init__(self, send_alert_callback):
        """
        Initialize unauthorized command handler.

        Args:
            send_alert_callback: Callback to send security alerts
        """
        self.send_alert_callback = send_alert_callback

    async def handle_unauthorized_attempt(self, command: str, message: Dict[str, Any]) -> None:
        """
        Handle command from unauthorized user.

        Args:
            command: Command that was attempted
            message: Telegram message with user info
        """
        user_info = message.get("from")
        if not isinstance(user_info, dict):
            user_info = {}

        username_value = user_info.get("username")
        username = username_value if isinstance(username_value, str) and username_value else UNKNOWN_TELEGRAM_USERNAME
        raw_user_id = user_info.get("id")
        user_id = str(raw_user_id) if raw_user_id is not None else UNKNOWN_TELEGRAM_USER_ID
        first_name_value = user_info.get("first_name")
        first_name = first_name_value if isinstance(first_name_value, str) else DEFAULT_TELEGRAM_FIRST_NAME
        last_name_value = user_info.get("last_name")
        last_name = last_name_value if isinstance(last_name_value, str) else DEFAULT_TELEGRAM_LAST_NAME
        full_name = f"{first_name} {last_name}".strip()

        security_alert = (
            f"🚨 UNAUTHORIZED TELEGRAM ACCESS ATTEMPT\n\n"
            f"👤 User: {full_name}\n"
            f"🆔 Username: @{username}\n"
            f"🔢 User ID: {user_id}\n"
            f"💬 Command: /{command}\n"
            f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await self.send_alert_callback(
            security_alert,
            AlertSeverity.CRITICAL,
            alert_type="security_breach",
        )

        logger.warning("Unauthorized user attempted command /%s: %s", command, user_info)
