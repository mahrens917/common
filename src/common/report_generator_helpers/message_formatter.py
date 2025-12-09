"""
Message formatter for simple messages.

Handles error messages and no-data messages for Telegram display.
"""


class MessageFormatter:
    """Formats simple messages for Telegram display."""

    @staticmethod
    def format_error_message(error_msg: str) -> str:
        """
        Format error message for Telegram display.

        Args:
            error_msg: Error message

        Returns:
            Formatted error message
        """
        return f"❌ **Error**\n\n{error_msg}\n\nPlease try again or contact support."

    @staticmethod
    def format_no_data_message(date_range: str) -> str:
        """
        Format message when no trade data is found.

        Args:
            date_range: Date range that was searched

        Returns:
            Formatted no data message
        """
        return f"📭 **No Trade Data**\n\nNo KXHIGH* trades found for {date_range}.\n\nTrades are collected from August 1, 2025 onwards."
