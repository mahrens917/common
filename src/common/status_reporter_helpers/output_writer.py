"""Output stream writer for status messages."""

import sys


class OutputWriter:
    """Handles writing status messages to output stream."""

    def __init__(self, output_stream=None):
        """
        Initialize the output writer.

        Args:
            output_stream: Where to write status messages (default: stdout)
        """
        self.output_stream = output_stream or sys.stdout

    def write(self, message: str) -> None:
        """Write a status message to the output stream."""
        try:
            print(message, file=self.output_stream, flush=True)
        except (BrokenPipeError, OSError):  # policy_guard: allow-silent-handler
            # Suppress broken pipe errors when stdout is closed (e.g., in subprocess)
            # Status messages are informational; service should continue running
            pass
