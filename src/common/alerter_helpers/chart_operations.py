"""Chart operations for Alerter."""

from typing import Optional


class ChartOperations:
    """Handles chart sending operations."""

    @staticmethod
    async def send_chart_image(
        telegram_enabled: bool,
        delivery_manager,
        authorized_user_ids: set,
        image_path: str,
        caption: str = "",
        target_user_id: Optional[str] = None,
    ) -> bool:
        """
        Send chart image.

        Args:
            telegram_enabled: Whether Telegram is enabled
            delivery_manager: Delivery manager instance
            authorized_user_ids: Set of authorized user IDs
            image_path: Path to image file
            caption: Optional caption
            target_user_id: Optional target user ID

        Returns:
            True if successful, False otherwise
        """
        if not telegram_enabled:
            return False

        recipients = [target_user_id] if target_user_id else list(authorized_user_ids)
        return (
            await delivery_manager.send_chart(image_path, caption, recipients)
            if recipients
            else False
        )
