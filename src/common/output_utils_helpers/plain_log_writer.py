"""Plain log writing utilities."""

import logging
from typing import Optional


class PlainLogWriter:
    """Writes plain text directly to file handlers."""

    @staticmethod
    def write_to_handlers(message: Optional[str]) -> bool:
        """
        Write message directly to file handlers.

        Args:
            message: Message to write

        Returns:
            True if written to at least one handler
        """
        message_to_write = PlainLogWriter._prepare_message(message)
        root_logger = logging.getLogger()

        wrote_plain = False
        for handler in root_logger.handlers:
            if PlainLogWriter._write_to_file_handler(handler, message_to_write):
                wrote_plain = True

        return wrote_plain

    @staticmethod
    def _prepare_message(message: Optional[str]) -> str:
        """Prepare message for writing."""
        if message is None:
            _none_guard_value = "\n"
            return _none_guard_value

        if not message.endswith("\n"):
            return f"{message}\n"

        return message

    @staticmethod
    def _write_to_file_handler(handler: logging.Handler, message: str) -> bool:
        """
        Write to a single file handler.

        Args:
            handler: Handler to write to
            message: Message to write

        Returns:
            True if written successfully
        """
        if not isinstance(handler, logging.FileHandler):
            return False

        try:
            handler.stream.write(message)
            handler.stream.flush()
        except (  # policy_guard: allow-silent-handler
            OSError,
            ValueError,
            AttributeError,
        ) as exc:
            logging.getLogger(__name__).debug(
                "Plain log write failed for handler %s: %s",
                handler,
                exc,
                exc_info=True,
            )
            return False
        else:
            return True
