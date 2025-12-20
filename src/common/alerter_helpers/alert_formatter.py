"""Alert message formatting for Telegram delivery."""

from ..alerting import Alert, AlertSeverity

DEFAULT_ALERT_EMOJI = "📢"


class AlertFormatter:
    """Formats alert messages for Telegram with severity-based emoji."""

    def format_telegram_message(self, alert: Alert) -> str:
        """
        Render a Telegram-ready message body for the supplied alert.

        Args:
            alert: Alert to format

        Returns:
            Formatted message with appropriate emoji
        """
        starts_with_emoji = len(alert.message) > 0 and (
            alert.message[0] in ["✅", "🚨", "📢", "❌", "📤", "📝", "🟢", "🔴"]
            or alert.message.startswith("⚠️")
            or alert.message.startswith("ℹ️")
        )

        if starts_with_emoji:
            formatted = alert.message
        else:
            severity_emoji = {
                AlertSeverity.INFO: "",
                AlertSeverity.WARNING: "⚠️",
                AlertSeverity.CRITICAL: "🚨",
            }
            emoji = severity_emoji.get(alert.severity, DEFAULT_ALERT_EMOJI)
            formatted = f"{emoji} {alert.message}"

        if alert.details and not starts_with_emoji:
            details_text = "\n".join(f"• {key}: {value}" for key, value in alert.details.items())
            formatted = f"{formatted}\n\nDetails:\n{details_text}"
        return formatted
