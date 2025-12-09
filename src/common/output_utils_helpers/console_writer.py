"""Console output utilities."""


class ConsoleWriter:
    """Handles console output with optional headers."""

    @staticmethod
    def write(message: str, level: str, headers: bool) -> None:
        """
        Write message to console.

        Args:
            message: Message to write
            level: Log level (for header formatting)
            headers: Whether to include timestamp and level headers
        """
        if headers:
            ConsoleWriter._write_with_headers(message, level)
        else:
            print(message)

    @staticmethod
    def _write_with_headers(message: str, level: str) -> None:
        """Write message with timestamp and level headers."""
        from ..time_utils import get_current_utc

        timestamp = get_current_utc().strftime("%Y-%m-%d %H:%M:%S")
        level_upper = level.upper()
        print(f"{timestamp} - {level_upper} - {message}")
