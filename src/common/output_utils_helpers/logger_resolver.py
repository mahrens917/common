"""Logger resolution utilities."""

import inspect
import logging
from typing import Optional


class LoggerResolver:
    """Resolves logger instances for output operations."""

    @staticmethod
    def get_logger(logger_name: Optional[str]) -> logging.Logger:
        """
        Get logger instance.

        Args:
            logger_name: Logger name to use (None = auto-detect caller)

        Returns:
            Logger instance
        """
        if logger_name:
            return logging.getLogger(logger_name)

        return LoggerResolver._get_caller_logger()

    @staticmethod
    def _get_caller_logger() -> logging.Logger:
        """Get logger for the calling module."""
        frame = inspect.currentframe()
        caller_module = "unknown"

        try:
            if frame is not None:
                caller_frame = frame.f_back
                if caller_frame is not None:
                    caller_module = LoggerResolver._extract_module_name(caller_frame)
        finally:
            # Ensure reference cycles are broken
            del frame

        return logging.getLogger(caller_module)

    @staticmethod
    def _extract_module_name(frame) -> str:
        """Extract module name from frame."""
        if "__name__" in frame.f_globals:
            return frame.f_globals["__name__"]
        return "unknown"
