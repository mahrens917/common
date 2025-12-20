"""Manages Telegram message and media delivery."""

import logging
from pathlib import Path
from typing import List

from ..alerting import Alert, TelegramDeliveryResult

logger = logging.getLogger(__name__)

ERR_NO_RECIPIENTS = "Telegram alert requires at least one recipient."


class TelegramDeliveryManager:
    """Coordinates message and media delivery to Telegram."""

    def __init__(
        self,
        message_sender,
        media_sender,
        alert_formatter,
    ):
        """
        Initialize delivery manager.

        Args:
            message_sender: Message sender helper
            media_sender: Media sender helper
            alert_formatter: Alert formatter helper
        """
        self.message_sender = message_sender
        self.media_sender = media_sender
        self.alert_formatter = alert_formatter

    async def send_alert(
        self,
        alert: Alert,
        recipients: List[str],
    ) -> TelegramDeliveryResult:
        """
        Send alert to Telegram recipients.

        Args:
            alert: Alert to send
            recipients: List of Telegram chat IDs

        Returns:
            TelegramDeliveryResult

        Raises:
            RuntimeError: When the alert cannot be delivered
        """
        if not recipients:
            raise ValueError(ERR_NO_RECIPIENTS)

        formatted_message = self.alert_formatter.format_telegram_message(alert)
        try:
            result = await self.message_sender.send_message(formatted_message, recipients)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to send Telegram alert: %s", exc, exc_info=True)
            return TelegramDeliveryResult(
                success=False, failed_recipients=list(recipients), queued_recipients=[]
            )
        if isinstance(result, TelegramDeliveryResult) and not result.success:
            logger.warning("Telegram alert delivery skipped/failed for %s", recipients)
        return result

    async def send_chart(
        self,
        image_path: str,
        caption: str,
        recipients: List[str],
    ) -> bool:
        """
        Send chart image to Telegram recipients.

        Args:
            image_path: Path to the image file
            caption: Caption for the image
            recipients: List of chat IDs

        Returns:
            True if sent successfully, False otherwise
        """
        if not recipients:
            logger.warning("Telegram chart send skipped; no authorized recipients configured")
            return False

        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            chart_name = caption if caption.strip() else image_path_obj.name
            logger.error(f"Chart file not found: '{chart_name}' (path: {image_path})")
            return False

        suffix = image_path_obj.suffix.lower()
        is_photo = suffix in {".png", ".jpg", ".jpeg", ".webp"}
        telegram_method = "sendPhoto" if is_photo else "sendDocument"

        try:
            result = await self.media_sender.send_media(
                source_path=image_path_obj,
                caption=caption,
                recipients=recipients,
                is_photo=is_photo,
                telegram_method=telegram_method,
            )
            if isinstance(result, TelegramDeliveryResult) and not result.success:
                logger.warning("Telegram media delivery skipped/failed for %s", recipients)
                return False
        except Exception as exc:
            chart_name = caption if caption.strip() else image_path_obj.name
            logger.error("Failed to send Telegram media '%s': %s", chart_name, exc, exc_info=True)
            return False

        return True
