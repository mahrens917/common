"""Formatters for basic status messages."""


class MessageFormatter:
    """Formats basic status messages with emojis and clear text."""

    @staticmethod
    def tracking_started() -> str:
        """Format tracking started message."""
        return "🔍 Tracking..."

    @staticmethod
    def markets_closed() -> str:
        """Format markets closed message."""
        return "🔒 Markets closed - waiting for next check"

    @staticmethod
    def markets_open() -> str:
        """Format markets open message."""
        return "✅ Markets open for trading"

    @staticmethod
    def scanning_markets(market_count: int) -> str:
        """Format scanning markets message."""
        return f"🔍 Scanning {market_count} markets for opportunities..."

    @staticmethod
    def initialization_complete() -> str:
        """Format initialization complete message."""
        return "🚀 Tracker initialized and ready"

    @staticmethod
    def shutdown_complete() -> str:
        """Format shutdown complete message."""
        return "🛑 Tracker shutdown complete"

    @staticmethod
    def checking_market_hours() -> str:
        """Format checking market hours message."""
        return "🕐 Checking market hours..."

    @staticmethod
    def error_occurred(error_message: str) -> str:
        """Format error message."""
        return f"❌ Error: {error_message}"
