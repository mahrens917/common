"""
Unified output utilities for console and log management.

This module provides a single function to handle all output scenarios
with flexible control over console/log destinations and header formatting.
"""

from typing import Optional


def output(
    message: str,
    level: str = "info",
    console: bool = True,
    log: bool = True,
    headers: bool = False,
    logger_name: Optional[str] = None,
    plain_log: bool = False,
):
    """
    Unified output function for console and/or log with optional headers

    Args:
        message: The message to output
        level: Log level (info, warning, error, debug, critical)
        console: Whether to print to console (default: True)
        log: Whether to log to file (default: True)
        headers: Whether to include headers in console output (default: False)
        logger_name: Logger name to use (default: calling module)
        plain_log: When True, bypasses standard logging formatting and writes the
            message directly to any configured file handlers (one message per line).

    Examples:
        # Clean console + logged (replaces print statements)
        output("🔪 Killing all existing service processes...")

        # Headers on console + logged (replaces logger.info)
        output("Service started successfully", headers=True)

        # Status reports - clean console only (no log spam)
        output(status_report, log=False)

        # Debug info - log only (no console clutter)
        output("Detailed debug info", console=False, level="debug")

        # Errors - headers everywhere for visibility
        output("Critical error occurred", level="error", headers=True)
    """
    from .output_utils_helpers import ConsoleWriter, LoggerResolver, PlainLogWriter

    # Get logger
    logger = LoggerResolver.get_logger(logger_name)

    # Console output
    if console:
        ConsoleWriter.write(message, level, headers)

    # Log to file
    if log:
        if plain_log:
            wrote_plain = PlainLogWriter.write_to_handlers(message)
            if not wrote_plain:
                log_method = getattr(logger, level.lower(), logger.info)
                log_method(message)
        else:
            log_method = getattr(logger, level.lower(), logger.info)
            log_method(message)
