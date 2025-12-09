"""Time duration formatting for status messages."""

# Constants
_CONST_60 = 60


class TimeFormatter:
    """Formats time durations in human-readable format."""

    @staticmethod
    def format_wait_duration(seconds: int) -> str:
        """
        Format wait duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted time string (e.g., "1 minute", "5m 30s", "45 seconds")
        """
        if seconds >= _CONST_60:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds == 0:
                if minutes == 1:
                    return "1 minute"
                return f"{minutes} minutes"
            return f"{minutes}m {remaining_seconds}s"

        if seconds == 1:
            return "1 second"
        return f"{seconds} seconds"

    @staticmethod
    def waiting_for_next_scan(seconds: int) -> str:
        """Format waiting for next scan message."""
        time_str = TimeFormatter.format_wait_duration(seconds)
        return f"⏳ Waiting {time_str} until next scan"
