"""Send media to Telegram recipients."""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MediaSender:
    """Sends media to individual recipients."""

    def __init__(self, telegram_client, timeout_seconds: int, backoff_manager):
        """Initialize media sender."""
        self.telegram_client = telegram_client
        self.timeout_seconds = timeout_seconds
        self.backoff_manager = backoff_manager

    async def send_to_all(
        self,
        recipients: list,
        payload_path: Path,
        caption: str,
        is_photo: bool,
        telegram_method: str,
    ) -> int:
        """Send media to all recipients and return success count."""
        success_count = 0
        for user_id in recipients:
            await self._send_to_recipient(user_id, payload_path, caption, is_photo, telegram_method)
            success_count += 1
            self.backoff_manager.clear_backoff()
            logger.debug("Telegram media %s delivered to user %s", payload_path.name, user_id)
        return success_count

    async def _send_to_recipient(self, user_id: str, payload_path: Path, caption: str, is_photo: bool, telegram_method: str) -> None:
        """Send media to a single recipient."""
        try:
            success, error_text = await self.telegram_client.send_media(
                user_id, payload_path, caption=caption, is_photo=is_photo, method=telegram_method
            )
        except asyncio.TimeoutError as exc:
            self.backoff_manager.record_failure(exc)
            raise RuntimeError(f"Telegram media timeout after {self.timeout_seconds}s for user {user_id}") from exc
        except (OSError, RuntimeError, ValueError) as exc:
            self.backoff_manager.record_failure(exc)
            raise RuntimeError(f"Telegram media send failed for user {user_id} with payload {payload_path}") from exc

        if not success:
            if error_text:
                failure_message = error_text
            else:
                failure_message = "unknown error"
            self.backoff_manager.record_failure(RuntimeError(failure_message))
            raise RuntimeError(f"Telegram media send returned failure for user {user_id}: {failure_message}")
