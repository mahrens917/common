"""Lifecycle and error status reporting functionality."""

from .base_reporter import WriterBackedReporter
from .message_formatter import MessageFormatter


class LifecycleReporter(WriterBackedReporter):
    """Handles lifecycle and error status reporting."""

    def error_occurred(self, error_message: str) -> None:
        """Report that an error occurred."""
        self._writer.write(MessageFormatter.error_occurred(error_message))

    def initialization_complete(self) -> None:
        """Report that initialization is complete."""
        self._writer.write(MessageFormatter.initialization_complete())

    def shutdown_complete(self) -> None:
        """Report that shutdown is complete."""
        self._writer.write(MessageFormatter.shutdown_complete())
